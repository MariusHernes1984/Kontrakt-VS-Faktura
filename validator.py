from database import sok_kontrakt, hent_kontrakt


def valider_faktura_mot_kontrakt(faktura_data, kontrakt):
    """Sammenligner fakturadata mot kontraktsvilkår og returnerer avviksrapport."""
    avvik = []
    advarsler = []
    ok = []

    # Sjekk timepris
    if kontrakt.get("timepris") and faktura_data.get("timepris"):
        faktura_timepris = float(faktura_data["timepris"])
        kontrakt_timepris = float(kontrakt["timepris"])

        if faktura_timepris > kontrakt_timepris:
            avvik.append({
                "felt": "Timepris",
                "type": "AVVIK",
                "faktura_verdi": f"{faktura_timepris:.2f} NOK",
                "kontrakt_verdi": f"{kontrakt_timepris:.2f} NOK",
                "differanse": f"+{faktura_timepris - kontrakt_timepris:.2f} NOK",
                "beskrivelse": (
                    f"Timepris på faktura ({faktura_timepris:.2f}) er høyere "
                    f"enn avtalt i kontrakt ({kontrakt_timepris:.2f})"
                ),
            })
        elif faktura_timepris < kontrakt_timepris:
            ok.append({
                "felt": "Timepris",
                "type": "OK",
                "faktura_verdi": f"{faktura_timepris:.2f} NOK",
                "kontrakt_verdi": f"{kontrakt_timepris:.2f} NOK",
                "beskrivelse": "Timepris er lik eller lavere enn avtalt.",
            })
        else:
            ok.append({
                "felt": "Timepris",
                "type": "OK",
                "faktura_verdi": f"{faktura_timepris:.2f} NOK",
                "kontrakt_verdi": f"{kontrakt_timepris:.2f} NOK",
                "beskrivelse": "Timepris stemmer med kontrakten.",
            })

    # Sjekk antall timer mot maks per måned
    if kontrakt.get("maks_timer_per_maaned") and faktura_data.get("antall_timer"):
        faktura_timer = float(faktura_data["antall_timer"])
        maks_timer = int(kontrakt["maks_timer_per_maaned"])

        if faktura_timer > maks_timer:
            avvik.append({
                "felt": "Antall timer",
                "type": "AVVIK",
                "faktura_verdi": f"{faktura_timer:.1f} timer",
                "kontrakt_verdi": f"Maks {maks_timer} timer/mnd",
                "differanse": f"+{faktura_timer - maks_timer:.1f} timer",
                "beskrivelse": (
                    f"Fakturerte timer ({faktura_timer:.1f}) overskrider "
                    f"maks avtalt ({maks_timer} timer/mnd)"
                ),
            })
        else:
            ok.append({
                "felt": "Antall timer",
                "type": "OK",
                "faktura_verdi": f"{faktura_timer:.1f} timer",
                "kontrakt_verdi": f"Maks {maks_timer} timer/mnd",
                "beskrivelse": "Antall timer er innenfor avtalt ramme.",
            })

    # Sjekk totalbeløp (timepris * timer)
    if (kontrakt.get("timepris") and faktura_data.get("antall_timer")
            and faktura_data.get("total_belop")):
        forventet = float(kontrakt["timepris"]) * float(faktura_data["antall_timer"])
        faktisk = float(faktura_data.get("total_eks_mva", 0) or faktura_data["total_belop"])

        # Tillat rabatt
        rabatt = float(kontrakt.get("avtalt_rabatt_prosent", 0))
        if rabatt > 0:
            forventet = forventet * (1 - rabatt / 100)

        toleranse = forventet * 0.01  # 1% toleranse for avrunding
        if faktisk > forventet + toleranse:
            avvik.append({
                "felt": "Totalbeløp",
                "type": "AVVIK",
                "faktura_verdi": f"{faktisk:.2f} NOK",
                "kontrakt_verdi": f"Forventet ~{forventet:.2f} NOK",
                "differanse": f"+{faktisk - forventet:.2f} NOK",
                "beskrivelse": (
                    f"Totalbeløp ({faktisk:.2f}) er høyere enn forventet "
                    f"basert på kontraktsvilkår ({forventet:.2f})"
                ),
            })
        else:
            ok.append({
                "felt": "Totalbeløp",
                "type": "OK",
                "faktura_verdi": f"{faktisk:.2f} NOK",
                "kontrakt_verdi": f"Forventet ~{forventet:.2f} NOK",
                "beskrivelse": "Totalbeløp stemmer med kontraktsvilkår.",
            })

    # Sjekk kontraktsperiode
    if kontrakt.get("sluttdato") and faktura_data.get("faktura_dato"):
        from datetime import datetime
        try:
            faktura_dato = datetime.strptime(faktura_data["faktura_dato"], "%Y-%m-%d")
            slutt_dato = datetime.strptime(kontrakt["sluttdato"], "%Y-%m-%d")
            if faktura_dato > slutt_dato:
                avvik.append({
                    "felt": "Kontraktsperiode",
                    "type": "AVVIK",
                    "faktura_verdi": faktura_data["faktura_dato"],
                    "kontrakt_verdi": f"Utløper {kontrakt['sluttdato']}",
                    "beskrivelse": (
                        "Fakturadato er etter kontraktens utløpsdato. "
                        "Kontrakten kan ha utløpt."
                    ),
                })
            else:
                ok.append({
                    "felt": "Kontraktsperiode",
                    "type": "OK",
                    "faktura_verdi": faktura_data["faktura_dato"],
                    "kontrakt_verdi": f"Utløper {kontrakt['sluttdato']}",
                    "beskrivelse": "Faktura er innenfor kontraktsperioden.",
                })
        except ValueError:
            advarsler.append({
                "felt": "Kontraktsperiode",
                "type": "ADVARSEL",
                "beskrivelse": "Kunne ikke tolke datoformat for sammenligning.",
            })

    # Sjekk prosjekt-ID-match
    if kontrakt.get("prosjekt_id") and faktura_data.get("prosjekt_id"):
        k_pid = kontrakt["prosjekt_id"].lower().strip()
        f_pid = faktura_data["prosjekt_id"].lower().strip()
        if k_pid != f_pid and k_pid not in f_pid and f_pid not in k_pid:
            advarsler.append({
                "felt": "Prosjekt-ID",
                "type": "ADVARSEL",
                "faktura_verdi": faktura_data["prosjekt_id"],
                "kontrakt_verdi": kontrakt["prosjekt_id"],
                "beskrivelse": (
                    "Prosjekt-ID på faktura samsvarer ikke med kontrakten. "
                    "Verifiser at fakturaen tilhører riktig prosjekt."
                ),
            })
        else:
            ok.append({
                "felt": "Prosjekt-ID",
                "type": "OK",
                "faktura_verdi": faktura_data["prosjekt_id"],
                "kontrakt_verdi": kontrakt["prosjekt_id"],
                "beskrivelse": "Prosjekt-ID stemmer med kontrakten.",
            })

    # Sjekk leverandørnavn-match
    if kontrakt.get("leverandor_navn") and faktura_data.get("leverandor_navn"):
        k_navn = kontrakt["leverandor_navn"].lower().strip()
        f_navn = faktura_data["leverandor_navn"].lower().strip()
        if k_navn not in f_navn and f_navn not in k_navn:
            advarsler.append({
                "felt": "Leverandørnavn",
                "type": "ADVARSEL",
                "faktura_verdi": faktura_data["leverandor_navn"],
                "kontrakt_verdi": kontrakt["leverandor_navn"],
                "beskrivelse": (
                    "Leverandørnavn på faktura samsvarer ikke nøyaktig "
                    "med kontrakten. Verifiser manuelt."
                ),
            })
        else:
            ok.append({
                "felt": "Leverandørnavn",
                "type": "OK",
                "faktura_verdi": faktura_data["leverandor_navn"],
                "kontrakt_verdi": kontrakt["leverandor_navn"],
                "beskrivelse": "Leverandørnavn stemmer.",
            })

    # Oppsummering
    total_sjekker = len(avvik) + len(advarsler) + len(ok)
    status = "GODKJENT"
    if avvik:
        status = "AVVIK FUNNET"
    elif advarsler:
        status = "ADVARSEL"

    return {
        "status": status,
        "kontrakt_id": kontrakt["id"],
        "kontrakt_nummer": kontrakt.get("kontrakt_nummer", ""),
        "avvik": avvik,
        "advarsler": advarsler,
        "ok": ok,
        "oppsummering": {
            "totalt_sjekket": total_sjekker,
            "antall_avvik": len(avvik),
            "antall_advarsler": len(advarsler),
            "antall_ok": len(ok),
        },
    }


def finn_og_valider(faktura_data):
    """Finner matching kontrakt og validerer faktura mot den."""
    kontrakter = sok_kontrakt(
        leverandor_navn=faktura_data.get("leverandor_navn"),
        prosjekt_id=faktura_data.get("prosjekt_id"),
    )

    if not kontrakter:
        return {
            "status": "INGEN KONTRAKT FUNNET",
            "beskrivelse": (
                f"Fant ingen kontrakt for leverandør "
                f"'{faktura_data.get('leverandor_navn', 'ukjent')}' "
                f"eller prosjekt-ID '{faktura_data.get('prosjekt_id', 'ukjent')}'."
            ),
            "faktura_data": faktura_data,
            "kontrakter_funnet": [],
        }

    # Valider mot beste match (første treff)
    beste_kontrakt = kontrakter[0]
    resultat = valider_faktura_mot_kontrakt(faktura_data, beste_kontrakt)
    resultat["faktura_data"] = faktura_data
    resultat["kontrakter_funnet"] = kontrakter

    return resultat
