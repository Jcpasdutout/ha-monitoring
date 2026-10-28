# Journal des modifications

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
