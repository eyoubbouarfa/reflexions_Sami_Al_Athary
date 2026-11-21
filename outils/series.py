# Référentiel des thèmes et des séries. C'est ici qu'on ajoute une série ou qu'on change un thème.
# "motifs" : morceaux de titre (minuscules, sans accents) qui reconnaissent la série à l'import Telegram.
# "type" : "cours" (cours de semaine, lecture d'un livre), "preche" (prêche du vendredi), "conference".

THEMES = [
    {"id": "aqida", "nom": "Croyance et unicité", "ar": "العقيدة والتوحيد"},
    {"id": "hadith", "nom": "Hadith", "ar": "الحديث"},
    {"id": "fiqh", "nom": "Jurisprudence", "ar": "الفقه"},
    {"id": "sira", "nom": "Biographie du Prophète ﷺ", "ar": "السيرة النبوية"},
    {"id": "coran", "nom": "Coran et exégèse", "ar": "القرآن والتفسير"},
    {"id": "tazkiya", "nom": "Spiritualité et rappels", "ar": "التزكية والمواعظ"},
    {"id": "manhaj", "nom": "Méthodologie et science", "ar": "المنهج والعلم"},
    {"id": "ramadan", "nom": "Ramadan", "ar": "رمضان"},
    {"id": "preches", "nom": "Prêches du vendredi", "ar": "خطب الجمعة"},
    {"id": "divers", "nom": "Conférences et divers", "ar": "متفرقات"},
]

S = lambda code, id, theme, nom, livre="", auteur="", type="cours", statut="terminée", motifs=(): {
    "code": code, "id": id, "theme": theme, "nom": nom, "livre": livre, "auteur": auteur,
    "type": type, "statut": statut, "motifs": list(motifs)}

SERIES = [
    # Cours de semaine en cours
    S("HU", "hadiths-unicite", "aqida", "Les hadiths sur l'unicité d'Allah", "", "Sheykh Salah al Budeyr", statut="en cours", motifs=["hadiths sur l'unicite"]),
    S("VU", "versets-unicite", "aqida", "Les versets du Coran sur l'unicité d'Allah", "", "Sheykh Mohamed Taqieddine al Hilaly", statut="en cours", motifs=["versets du coran sur l'unicite"]),
    S("LF", "lumiere-foi", "aqida", "La lumière de la foi et les ténèbres de l'hypocrisie", "نور الإيمان وظلمات النفاق", "Sheykh Said ibn Wahf al Qahtany", statut="en cours", motifs=["lumiere de la foi"]),
    S("TJ", "tajrid", "hadith", "Le résumé du Sahih d'al Boukhary", "التجريد الصريح لأحاديث الجامع الصحيح", "Az-Zoubaydi", statut="en cours", motifs=["tajrid", "resume du sahih"]),
    S("SJ", "sahih-jami", "hadith", "Lecture de Sahih al Jami'", "صحيح الجامع الصغير", "Sheykh al Albâny", statut="en cours", motifs=["sahih al jami"]),
    S("MW", "muwatta", "fiqh", "Lecture et étude du Muwatta", "الموطأ", "L'imam Malik ibn Anas", statut="en cours", motifs=["muwatta"]),
    S("SR", "sira-ramadan-1441", "sira", "La biographie du Prophète ﷺ (Ramadan 1441)", "", "", motifs=["ramadan 1441/2020"]),
    S("SQ", "sira-qr", "sira", "La biographie du Prophète ﷺ en questions-réponses", "أمالي في السيرة النبوية", "", motifs=["biographie du prophete", "questions reponses"]),
    S("DM", "decouverte-messager", "sira", "À la découverte du Messager d'Allah ﷺ", "", "", statut="en cours", motifs=["decouverte du messager"]),
    # Cours de semaine terminés
    S("BR", "sira-resumee", "sira", "La biographie résumée du Prophète ﷺ", "المختصر المفيد في السيرة النبوية", "", motifs=["biographie resumee"]),
    S("IQ", "citations-ibn-qayim", "tazkiya", "Les citations spirituelles de l'imam Ibn al Qayim", "مواعظ ابن القيم", "Ibn al Qayim", motifs=["citations spirituelles de l'imam ibn al qayim"]),
    S("IT", "citations-ibn-taymiyah", "tazkiya", "Les citations spirituelles de Sheykh al Islam Ibn Taymiyah", "مواعظ شيخ الإسلام ابن تيمية", "Ibn Taymiyah", motifs=["citations spirituelles de sheykh al islam"]),
    S("TS", "tahdhir-sajid", "aqida", "La mise en garde contre le fait de prendre les tombes comme lieux de culte", "تحذير الساجد من اتخاذ القبور مساجد", "Sheykh al Albâny", motifs=["tombes"]),
    S("MU", "merites-oeuvres", "hadith", "Les mérites des bonnes œuvres", "", "Al Hafidh al Mundhiry", motifs=["merites des bonnes"]),
    S("MQ", "merite-mecque", "hadith", "Les 40 hadiths sur le mérite de la Mecque", "", "", motifs=["merite de la mecque"]),
    S("PC", "paraboles-coran", "coran", "Les paraboles du Coran", "", "", motifs=["paraboles du coran"]),
    S("CQ", "comprendre-coran", "coran", "Comment comprendre le Coran", "", "Sheykh ibn Otheymine", motifs=["comment comprendre le coran"]),
    S("HM", "hisnul-muslim", "tazkiya", "Explication de la citadelle du musulman", "إتحاف المسلم بشرح حصن المسلم", "", motifs=["citadelle du musulman", "hisnul"]),
    S("OT", "perfection-religion", "manhaj", "La perfection de la religion et le danger de l'innovation", "", "Sheykh Mohammed ibn Salih al Otheymine", motifs=["perfection de la religion"]),
    S("BZ", "se-corriger-precheurs", "manhaj", "La manière de se corriger entre prêcheurs", "", "Sheykh abd al Aziz ibn Bâz", motifs=["se corriger entre precheurs"]),
    S("DS", "divergences-savants", "manhaj", "Les divergences entre les savants", "", "Sheykh ibn Otheymine", motifs=["divergences entre les savants"]),
    S("UM", "union-musulmans", "manhaj", "L'union des musulmans", "", "Sheykh al Islam ibn Taymiyyah", motifs=["union des musulmans"]),
    S("UF", "union-foi", "manhaj", "L'union fait la foi", "", "Sheykh abd Rahman ibn Nasir as-Saady", motifs=["union fait la foi"]),
    S("GP", "bonne-pensee", "tazkiya", "Garder une bonne pensée d'Allah", "حسن الظن بالله", "Ibn abi Dounya", motifs=["bonne pensee d'allah"]),
    S("HS", "hommage-savoir", "manhaj", "Hommage au savoir", "تعظيم العلم", "Sheykh Salih al Oseymi", motifs=["hommage au savoir"]),
    S("RB", "30-lecons-ramadan", "ramadan", "30 leçons pour le mois de Ramadan", "", "Sheykh abd Razzâq al Badr", motifs=["30 lecons pour le mois de ramadan"]),
    S("IB", "fatwas-ibn-baz-jeune", "ramadan", "Les avis juridiques de Sheykh ibn Bâz sur le jeûne", "", "Sheykh abd al Aziz ibn Bâz", motifs=["avis juridiques de sheykh ibn baz"]),
    # Prêches du vendredi
    S("SV", "compagnons", "preches", "Les Compagnons du Messager d'Allah ﷺ", "", "", "preche", "en cours", motifs=["le merite de", "le merite d'", "le merite d’", "merite des compagnons"]),
    S("RM", "reponses-messager", "preches", "Les réponses du Messager d'Allah ﷺ", "", "", "preche", motifs=["reponses du messager"]),
    S("PM", "pedagogie-messager", "preches", "La pédagogie du Messager d'Allah ﷺ", "", "", "preche", motifs=["pedagogie du messager"]),
    S("SC", "specificites", "preches", "Les spécificités du Messager ﷺ et de sa communauté", "", "", "preche", motifs=["specificites"]),
    S("AD", "au-dela", "preches", "Le Jour dernier et l'au-delà", "", "", "preche", motifs=["resurrection", "au-dela", "enfer", "paradis"]),
    S("KH", "sourate-kahf", "preches", "L'explication de sourate al Kahf", "", "", "preche", motifs=["sourate al kahf"]),
    S("CO", "preches-coran", "preches", "Le Coran, le livre du Ramadan", "", "", "preche", motifs=["lecture du coran", "le mois du coran"]),
    S("RI", "ramadan-invocations", "preches", "Le Ramadan est le mois des invocations", "", "", "preche", motifs=["mois des invocations"]),
    S("PT", "merites-piete", "preches", "Les mérites de la piété dans le Noble Coran", "", "", "preche", motifs=["merites de la piete"]),
    S("VY", "priere-voyageur", "preches", "Quelques règles relatives à la prière du voyageur", "", "", "preche", motifs=["priere du voyageur"]),
    S("SI", "preches-isoles", "preches", "Prêches isolés", "", "", "preche", motifs=["sermon du vendredi"]),
    S("AID", "khotbas-aid", "preches", "Khotbas des deux fêtes", "", "", "preche", motifs=["khotba du aid", "sermon du aid"]),
    # Divers
    S("CF", "conferences", "divers", "Conférences et rappels", "", "", "conference", motifs=[]),
]
