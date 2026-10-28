# Monitoring

Le monitoring tourne directement dans Home Assistant : sondes mail IMAP, sites et API HTTP, ping / port TCP et machines SNMP, avec le tableau de bord dans la barre latérale.

## Premier démarrage

1. Démarrez l'add-on, puis cliquez **Ouvrir l'interface Web** (ou **Monitoring** dans la barre latérale).
2. Allez dans **Sondes** et créez le compte administrateur.
3. Ajoutez vos sondes.

Les sondes, mots de passe et l'historique sont dans le dossier `/data` de l'add-on : ils sont conservés lors des mises à jour et inclus dans les sauvegardes de Home Assistant.

## Reprendre les sondes d'une autre installation

Pour retrouver les sondes d'un monitoring existant (par exemple un conteneur Proxmox) :

1. Arrêtez l'ancien monitoring et récupérez son fichier `monitoring.db` (sous Proxmox : `/var/lib/monitoring/monitoring.db`).
2. Déposez-le dans le dossier `share/monitoring/` de Home Assistant (avec l'add-on **Samba share** ou **Studio Code Server**).
3. Démarrez l'add-on. La base n'est reprise que si l'add-on n'en a pas encore : déposez donc le fichier **avant le premier démarrage**. Si l'add-on a déjà démarré, désinstallez-le puis réinstallez-le (ce qui efface les sondes créées entre-temps).

Le compte administrateur et les jetons d'accès sont repris avec.

## Accès direct et intégration Home Assistant

Pour avoir les sondes comme entités dans Home Assistant, installez aussi l'intégration **Monitoring** via HACS (même dépôt). L'add-on se signale tout seul : après le redémarrage de Home Assistant, **Paramètres** → **Appareils et services** affiche « Nouvel appareil découvert : Monitoring ». Cliquez **Ajouter**, puis **Valider** : il n'y a ni adresse ni jeton à saisir. Un jeton « Home Assistant (add-on) » est créé pour cela dans le monitoring ; si vous le supprimez, il est recréé au prochain démarrage de l'add-on.

Le port **8080** de la machine Home Assistant donne aussi accès au monitoring (par exemple `http://homeassistant.local:8080`). Il n'est plus nécessaire à l'intégration.

Pour changer ce port, ou le fermer si vous n'utilisez pas l'intégration, allez dans l'onglet **Configuration** de l'add-on, section **Réseau**.

## Options

- **Réinitialiser le compte administrateur** (`reset_admin`) : en cas de mot de passe oublié, activez l'option et redémarrez l'add-on, recréez le compte depuis la page **Sondes**, puis désactivez l'option.

## Ping

Les sondes ping utilisent la commande `ping` du conteneur ; elles fonctionnent sans réglage particulier.
