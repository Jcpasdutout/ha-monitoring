# Journal des modifications

## 2.10.1

- Dans Home Assistant, les fenêtres ouvertes depuis le menu (Exporter, Importer, Jetons d'accès, mot de passe) s'affichent au centre de l'écran au lieu de rester cachées dans le menu flottant.

## 2.10.0

- Menu administrateur : **Exporter les sondes** (fichier JSON, historique en option) et **Importer une sauvegarde** (ajouter aux sondes actuelles ou les remplacer). Pratique pour passer du conteneur Proxmox à l'add-on, ou l'inverse. Le fichier contient les mots de passe des sondes : gardez-le en lieu sûr.

## 2.9.2

- Dans Home Assistant, la page Sondes n'affiche plus d'ascenseurs inutiles (les interrupteurs « Active » débordaient de la page).

## 2.9.1

- Hors Home Assistant, la barre du haut n'affiche plus le logo ni le titre « Monitoring » (aucun changement dans HA).

## 2.9.0

- Le choix du thème passe dans le menu roue crantée : Sombre, Clair, Image ou Transparent. La galerie d'images n'apparaît qu'en mode Image, et recliquer sur l'image choisie bascule entre sa version claire et sa version sombre.

## 2.8.0

- Image de fond au choix dans le menu roue crantée : sept fonds intégrés (clairs et sombres) ou ta propre image, avec un voile réglable et des cartes en verre dépoli. En mode transparent, le fond du thème Home Assistant reste affiché sauf si « Garder l'image en mode transparent » est coché.

## 2.7.0

- Nouveau bouton dans le menu flottant (visible seulement dans Home Assistant) : plein écran, qui masque la barre latérale et le bandeau de Home Assistant, ou retour à l'affichage normal. Le choix est mémorisé.

## 2.6.1

- Découverte automatique : le jeton du Supervisor est maintenant retrouvé (l'image de base le retirait de l'environnement), ce qui corrige le refus « 403 Forbidden ».

## 2.6.0

- Les numéros de version de l'add-on et de l'application s'affichent en bas du menu roue crantée.

## 2.5.2

- Découverte automatique : correctif pour l'erreur « HTTP Error 403: Forbidden » (accès à l'API du Supervisor, nom d'hôte de secours) et message d'erreur plus précis dans le journal.

## 2.5.1

- Fond transparent : l'image ou le dégradé de fond du thème Home Assistant (`lovelace-background`) s'affiche maintenant derrière le monitoring, plus seulement la couleur unie.

## 2.5.0

- Le bouton de thème passe en cycle : fond clair → sombre → transparent. Le fond transparent laisse voir le fond du thème Home Assistant et suit automatiquement son mode clair ou sombre.

## 2.4.1

- Le menu flottant s'affiche dès que le monitoring est intégré dans HA (panneau de l'add-on, ou carte/panneau « page web »).
- Après une mise à jour, la nouvelle interface s'affiche tout de suite (la page n'est plus gardée en cache par le navigateur).

## 2.4.0

- Un seul bandeau en haut : dans le panneau de l'add-on, le menu du monitoring (onglets, Actualiser, thème, réglages, compte) devient une petite barre flottante en bas à droite, sous le bandeau de Home Assistant.

## 2.3.0

- L'intégration Monitoring détecte l'add-on toute seule : Home Assistant propose de l'ajouter en un clic, sans adresse ni jeton à saisir (jeton « Home Assistant (add-on) » créé automatiquement).

## 2.2.0

- Première version de l'add-on : tableau de bord dans la barre latérale (Ingress), base dans `/data`.
- Le monitoring fonctionne sous un préfixe d'URL (chemins relatifs, cookie limité au chemin de l'Ingress).
