import os
import json
from flask import (
    Flask, render_template, request, redirect, url_for, flash, jsonify,
    send_from_directory, Response
)
from werkzeug.utils import secure_filename
from database import (
    init_db, opprett_kontrakt, hent_alle_kontrakter, hent_kontrakt,
    slett_kontrakt, lagre_faktura_logg, hent_faktura_logg, hent_faktura,
    slett_faktura, opprett_varslingsmottaker, hent_alle_varslingsmottakere,
    hent_varslingsmottakere_for_leverandor, oppdater_varslingsmottaker,
    slett_varslingsmottaker, oppdater_kontrakt_fil, get_db
)
from analyzer import analyser_faktura, analyser_kontrakt_tekst
from pdf_extractor import ekstraher_tekst as ekstraher_pdf_tekst
from validator import finn_og_valider
from report_generator import generer_avviksrapport
from email_client import send_avviksvarsling
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "poc-hemmelig-nokkel-2024")

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
CONTRACTS_FOLDER = os.path.join(os.path.dirname(__file__), "kontrakt_filer")
ALLOWED_EXTENSIONS = {"pdf"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB maks


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def dashboard():
    kontrakter = hent_alle_kontrakter()
    fakturaer = hent_faktura_logg()
    statistikk = {
        "antall_kontrakter": len(kontrakter),
        "antall_fakturaer": len(fakturaer),
        "antall_avvik": sum(1 for f in fakturaer if f["status"] == "AVVIK FUNNET"),
        "antall_godkjent": sum(1 for f in fakturaer if f["status"] == "GODKJENT"),
    }
    return render_template(
        "index.html",
        kontrakter=kontrakter,
        fakturaer=fakturaer,
        statistikk=statistikk,
    )


@app.route("/kontrakter")
def kontrakter_liste():
    kontrakter = hent_alle_kontrakter()
    return render_template("contracts.html", kontrakter=kontrakter)


@app.route("/kontrakter/ny", methods=["GET", "POST"])
def ny_kontrakt():
    if request.method == "POST":
        data = {
            "leverandor_navn": request.form["leverandor_navn"],
            "prosjekt_id": request.form.get("prosjekt_id", ""),
            "kontrakt_nummer": request.form.get("kontrakt_nummer", ""),
            "timepris": float(request.form.get("timepris", 0) or 0),
            "maks_timer_per_maaned": int(request.form.get("maks_timer_per_maaned", 0) or 0),
            "sla_responstid_timer": int(request.form.get("sla_responstid_timer", 0) or 0),
            "avtalt_rabatt_prosent": float(request.form.get("avtalt_rabatt_prosent", 0) or 0),
            "valuta": request.form.get("valuta", "NOK"),
            "startdato": request.form.get("startdato", ""),
            "sluttdato": request.form.get("sluttdato", ""),
            "beskrivelse": request.form.get("beskrivelse", ""),
            "kontakt_person": request.form.get("kontakt_person", ""),
            "kontakt_epost": request.form.get("kontakt_epost", ""),
        }

        # Advar ved duplikat kontraktsnummer (men blokker ikke)
        if data["kontrakt_nummer"]:
            conn = get_db()
            eksisterer = conn.execute(
                "SELECT id FROM kontrakter WHERE kontrakt_nummer = ?",
                (data["kontrakt_nummer"],),
            ).fetchone()
            conn.close()
            if eksisterer:
                flash(
                    f"Advarsel: Kontraktsnummer {data['kontrakt_nummer']} finnes allerede.",
                    "warning",
                )

        kontrakt_id = opprett_kontrakt(data)

        # Hvis vi har en pending opplastet PDF (fra last-opp-flyten), koble den til
        pending_pdf = request.form.get("pending_pdf", "").strip()
        if pending_pdf:
            oppdater_kontrakt_fil(kontrakt_id, pending_pdf)

        flash("Kontrakt opprettet!", "success")
        return redirect(url_for("kontrakter_liste"))
    return render_template("contract_form.html")


@app.route("/kontrakter/last-opp", methods=["GET", "POST"])
def last_opp_kontrakt():
    if request.method == "POST":
        if "kontrakt" not in request.files:
            flash("Ingen fil valgt.", "error")
            return redirect(request.url)

        fil = request.files["kontrakt"]
        if fil.filename == "":
            flash("Ingen fil valgt.", "error")
            return redirect(request.url)

        if not allowed_file(fil.filename):
            flash("Kun PDF-filer er tillatt.", "error")
            return redirect(request.url)

        filnavn = secure_filename(fil.filename)
        filbane = os.path.join(CONTRACTS_FOLDER, filnavn)
        fil.save(filbane)

        # Steg 1: ekstraher tekst (med OCR-fallback)
        tekst, brukte_ocr = ekstraher_pdf_tekst(filbane)
        if not tekst:
            flash(
                "Kunne ikke lese tekst fra PDF-en (verken via PyPDF2 eller OCR).",
                "error",
            )
            return redirect(request.url)

        # Steg 2: AI-analyse
        resultat = analyser_kontrakt_tekst(tekst)
        if "feil" in resultat:
            flash(f"AI-analyse feilet: {resultat['feil']}", "error")
            return redirect(request.url)

        if not resultat.get("er_kontrakt", True):
            flash(
                "Dokumentet ser ikke ut som en kontrakt. Sjekk filen og prøv igjen.",
                "error",
            )
            return redirect(request.url)

        felter = resultat.get("felter", {})
        advarsler = resultat.get("advarsler", [])

        if brukte_ocr:
            advarsler = ["Tekst hentet via OCR — verifiser nøye."] + advarsler

        # Sjekk duplikat-kontraktsnummer
        kontrakt_nummer = (felter.get("kontrakt_nummer") or {}).get("verdi")
        if kontrakt_nummer:
            conn = get_db()
            eksisterer = conn.execute(
                "SELECT id FROM kontrakter WHERE kontrakt_nummer = ?",
                (kontrakt_nummer,),
            ).fetchone()
            conn.close()
            if eksisterer:
                advarsler.append(
                    f"Kontraktsnummer {kontrakt_nummer} finnes allerede i databasen."
                )

        return render_template(
            "contract_form.html",
            felter=felter,
            advarsler=advarsler,
            brukte_ocr=brukte_ocr,
            pending_pdf=filnavn,
        )

    return render_template("contract_upload.html")


@app.route("/kontrakter/<int:kontrakt_id>/slett", methods=["POST"])
def slett_kontrakt_route(kontrakt_id):
    slett_kontrakt(kontrakt_id)
    flash("Kontrakt slettet.", "info")
    return redirect(url_for("kontrakter_liste"))


@app.route("/kontrakter/<int:kontrakt_id>")
def vis_kontrakt(kontrakt_id):
    kontrakt = hent_kontrakt(kontrakt_id)
    if not kontrakt:
        flash("Kontrakt ikke funnet.", "error")
        return redirect(url_for("kontrakter_liste"))
    return render_template("contract_detail.html", kontrakt=kontrakt)


@app.route("/kontrakter/<int:kontrakt_id>/pdf")
def last_ned_kontrakt_pdf(kontrakt_id):
    kontrakt = hent_kontrakt(kontrakt_id)
    if not kontrakt or not kontrakt.get("fil_path"):
        flash("Ingen PDF tilgjengelig for denne kontrakten.", "error")
        return redirect(url_for("kontrakter_liste"))
    return send_from_directory(
        CONTRACTS_FOLDER, kontrakt["fil_path"], as_attachment=False
    )


@app.route("/last-opp", methods=["GET", "POST"])
def last_opp_faktura():
    if request.method == "POST":
        if "faktura" not in request.files:
            flash("Ingen fil valgt.", "error")
            return redirect(request.url)

        fil = request.files["faktura"]
        if fil.filename == "":
            flash("Ingen fil valgt.", "error")
            return redirect(request.url)

        if fil and allowed_file(fil.filename):
            filnavn = secure_filename(fil.filename)
            filbane = os.path.join(app.config["UPLOAD_FOLDER"], filnavn)
            fil.save(filbane)

            # Analyser faktura med AI
            flash("Analyserer faktura med AI...", "info")
            faktura_data = analyser_faktura(filbane)

            if "feil" in faktura_data:
                flash(f"Feil ved analyse: {faktura_data['feil']}", "error")
                return redirect(request.url)

            # Valider mot kontrakt
            resultat = finn_og_valider(faktura_data)

            # Lagre i logg
            logg_data = {
                "filnavn": filnavn,
                "leverandor_navn": faktura_data.get("leverandor_navn", ""),
                "prosjekt_id": faktura_data.get("prosjekt_id", ""),
                "faktura_nummer": faktura_data.get("faktura_nummer", ""),
                "faktura_dato": faktura_data.get("faktura_dato", ""),
                "forfallsdato": faktura_data.get("forfallsdato", ""),
                "total_belop": faktura_data.get("total_belop", 0),
                "timepris": faktura_data.get("timepris", 0),
                "antall_timer": faktura_data.get("antall_timer", 0),
                "kontrakt_id": resultat.get("kontrakt_id"),
                "status": resultat["status"],
                "avvik_rapport": json.dumps(resultat, ensure_ascii=False, default=str),
            }
            logg_id = lagre_faktura_logg(logg_data)

            # Send e-postvarsling ved avvik eller advarsel
            if resultat["status"] in ("AVVIK FUNNET", "ADVARSEL"):
                try:
                    leverandor = faktura_data.get("leverandor_navn", "")
                    mottakere = hent_varslingsmottakere_for_leverandor(leverandor)

                    if mottakere:
                        pdf_bytes = generer_avviksrapport(faktura_data, resultat)
                        sendt_til = []
                        feilet = []
                        for m in mottakere:
                            epost_resultat = send_avviksvarsling(
                                mottaker_epost=m["epost"],
                                faktura=faktura_data,
                                rapport=resultat,
                                pdf_bytes=pdf_bytes,
                            )
                            if epost_resultat["success"]:
                                sendt_til.append(m["epost"])
                            else:
                                feilet.append(m["epost"])
                        if sendt_til:
                            flash(f"Avviksvarsling sendt til {', '.join(sendt_til)}", "success")
                        if feilet:
                            flash(f"Kunne ikke sende til: {', '.join(feilet)}", "warning")
                except Exception as e:
                    flash(f"E-postvarsling feilet: {str(e)}", "warning")

            return redirect(url_for("vis_resultat", faktura_id=logg_id))
        else:
            flash("Kun PDF-filer er tillatt.", "error")
            return redirect(request.url)

    return render_template("upload.html")


@app.route("/resultat/<int:faktura_id>")
def vis_resultat(faktura_id):
    faktura = hent_faktura(faktura_id)
    if not faktura:
        flash("Faktura ikke funnet.", "error")
        return redirect(url_for("dashboard"))

    avvik_rapport = json.loads(faktura["avvik_rapport"]) if faktura.get("avvik_rapport") else {}
    return render_template("result.html", faktura=faktura, rapport=avvik_rapport)


@app.route("/faktura/<int:faktura_id>/rapport")
def last_ned_rapport(faktura_id):
    faktura = hent_faktura(faktura_id)
    if not faktura:
        flash("Faktura ikke funnet.", "error")
        return redirect(url_for("dashboard"))

    avvik_rapport = json.loads(faktura["avvik_rapport"]) if faktura.get("avvik_rapport") else {}
    if not avvik_rapport.get("avvik") and not avvik_rapport.get("advarsler"):
        flash("Ingen avvik eller advarsler a rapportere.", "info")
        return redirect(url_for("vis_resultat", faktura_id=faktura_id))

    pdf_bytes = generer_avviksrapport(faktura, avvik_rapport)
    fnr = faktura.get("faktura_nummer", f"id-{faktura_id}").replace("/", "-")
    filnavn = f"Avviksrapport_{fnr}.pdf"

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filnavn}"},
    )


@app.route("/faktura/<int:faktura_id>/pdf")
def vis_faktura_pdf(faktura_id):
    faktura = hent_faktura(faktura_id)
    if not faktura or not faktura.get("filnavn"):
        flash("Ingen PDF tilgjengelig for denne fakturaen.", "error")
        return redirect(url_for("dashboard"))
    return send_from_directory(
        UPLOAD_FOLDER, faktura["filnavn"], as_attachment=False
    )


@app.route("/historikk")
def historikk():
    fakturaer = hent_faktura_logg()
    return render_template("history.html", fakturaer=fakturaer)


@app.route("/faktura/<int:faktura_id>/slett", methods=["POST"])
def slett_faktura_route(faktura_id):
    slett_faktura(faktura_id)
    flash("Faktura slettet.", "info")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/varsling")
def varsling():
    mottakere = hent_alle_varslingsmottakere()
    kontrakter = hent_alle_kontrakter()
    leverandorer = sorted(set(k["leverandor_navn"] for k in kontrakter if k.get("leverandor_navn")))
    return render_template("varsling.html", mottakere=mottakere, leverandorer=leverandorer)


@app.route("/varsling/ny", methods=["POST"])
def ny_varslingsmottaker():
    epost = request.form.get("epost", "").strip()
    leverandor = request.form.get("leverandor_navn", "").strip() or None

    if not epost:
        flash("E-postadresse er pakrevd.", "error")
        return redirect(url_for("varsling"))

    opprett_varslingsmottaker(epost, leverandor)
    if leverandor:
        flash(f"Varslingsmottaker {epost} lagt til for {leverandor}.", "success")
    else:
        flash(f"Varslingsmottaker {epost} lagt til for alle leverandorer.", "success")
    return redirect(url_for("varsling"))


@app.route("/varsling/<int:mottaker_id>/toggle", methods=["POST"])
def toggle_varslingsmottaker(mottaker_id):
    aktiv = request.form.get("aktiv") == "1"
    oppdater_varslingsmottaker(mottaker_id, aktiv)
    flash("Varslingsmottaker oppdatert.", "info")
    return redirect(url_for("varsling"))


@app.route("/varsling/<int:mottaker_id>/slett", methods=["POST"])
def slett_varslingsmottaker_route(mottaker_id):
    slett_varslingsmottaker(mottaker_id)
    flash("Varslingsmottaker slettet.", "info")
    return redirect(url_for("varsling"))


os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONTRACTS_FOLDER, exist_ok=True)
init_db()


def _auto_seed_hvis_tom():
    """Populerer database + PDF-er hvis databasen er tom (f.eks. etter redeploy)."""
    try:
        if hent_alle_kontrakter():
            return
        print("Database er tom — kjører auto-seed...")
        import seed_data, seed_extra, generate_contracts, generate_invoices
        seed_data.seed()
        seed_extra.seed()
        generate_contracts.generer_alle()
        generate_invoices.generer_alle()
        print("Auto-seed ferdig.")
    except Exception as e:
        print(f"Auto-seed feilet: {e}")


_auto_seed_hvis_tom()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1", port=5000)
