# Sami al Athary · Cours

Application web installable qui rassemble les cours, prêches et rappels du frère Sami al Athary, classés par thème, par livre étudié et par épisode.

Réalisation : Eyoub Bouarfa

## Contenu
- **Accueil** : dernier prêche du vendredi, livres en cours d'étude, derniers cours publiés.
- **Thèmes** : croyance, hadith, jurisprudence, sîra, Coran, spiritualité, méthodologie, Ramadan, conférences. Chaque livre a sa page avec tous ses épisodes dans l'ordre.
- **Vendredi** : les prêches, par cycle.
- **Recherche** : un mot ou une phrase, dans les titres et dans le contenu des cours transcrits.
- **Direct** : lien vers le cours en direct quand il a lieu.

Chaque utilisateur peut marquer les cours écoutés et reprendre un livre là où il s'est arrêté (mémorisé sur son téléphone).

## Mettre en ligne (GitHub Pages)
1. Créer un dépôt, y déposer tout le contenu de ce dossier.
2. Settings > Pages > Branch `main` / dossier racine.
3. L'adresse s'affiche après une minute. Sur téléphone : « Ajouter à l'écran d'accueil ».

## Mise à jour automatique
Deux fois par jour, GitHub lit le canal Telegram et le compte SoundCloud, classe les nouveaux cours par leur titre et met l'appli à jour (`outils/synchro.py`). Aucune cadence n'est supposée : un cours manqué ou décalé ne change rien au classement.

Pour relire tout le canal (dates, cours manquants) : onglet Actions > Synchronisation des cours > Run workflow > cocher « Relire tout le canal ».

Un cours non reconnu est rangé dans « Conférences » et signalé dans le journal : ajouter la série dans `outils/series.py`.

## Lancer un direct
Dans `data/config.json`, mettre `"actif": true`, un titre et le lien du direct (YouTube non répertorié, par exemple), puis pousser. Remettre `false` à la fin.

## Notes de cours et PDF
1. `python outils/transcrire.py <série>` : transcription automatique sur le PC (dossier `transcriptions/`, jamais publié).
2. Rédaction des notes propres et illustrées dans `notes/<id>.md` (format décrit dans `outils/publier_notes.py`).
3. Relecture par l'enseignant, puis `valide: oui` en tête du fichier.
4. `python outils/publier_notes.py` : les notes apparaissent dans l'appli, téléchargeables en PDF et cherchables.

## Supports des livres
Dans `data/series.json`, ajouter `"support": "<lien>"` à la série concernée. Le bouton « Support du livre » apparaît automatiquement.
