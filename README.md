# Monitoring pour Home Assistant

Intégration Home Assistant pour le **monitoring maison** (sondes mail IMAP, sites et API HTTP, ping / port TCP, machines SNMP).
Chaque sonde devient un **appareil** dans Home Assistant, avec ses capteurs. Quand vous ajoutez, renommez ou supprimez une sonde dans le monitoring, Home Assistant suit tout seul.

## Ce que vous obtenez

**Pour chaque sonde**

| Entité | Types de sonde | Contenu |
|---|---|---|
| Problème (capteur binaire) | toutes | allumé en cas d'alerte ou d'erreur |
| État | toutes | OK, Alerte, Erreur, En attente, En pause (attribut `resume` : le texte affiché sur le tableau de bord) |
| Dernière vérification | toutes | date de la dernière vérification |
| Vérifier maintenant (bouton) | toutes | relance la sonde tout de suite |
| Mails non lus | IMAP | nombre de mails non lus ; attributs `dossiers` et `derniers_mails` (expéditeur, objet, date) |
| Temps de réponse, Code HTTP, Valeur JSON | HTTP | la valeur JSON n'apparaît que si un chemin JSON est configuré |
| Latence, Pertes | ping / TCP | en ms et en % |
| CPU, RAM, chaque disque, OID personnalisé | SNMP | en %, une entité par jauge ; plus « Allumée depuis » (jours) |

**Pour l'ensemble (appareil « Monitoring »)** : nombre de sondes en alerte ou en erreur (avec leur liste), nombre de sondes en erreur, total des mails non lus, un capteur binaire « Problème sur une sonde » et un bouton « Relancer toutes les sondes ».

## Deux façons de faire tourner le monitoring

Ce dépôt contient aussi un **add-on** Home Assistant (dossier `monitoring/`) : le monitoring tourne alors directement dans Home Assistant, avec son tableau de bord dans la barre latérale. Il faut Home Assistant **OS** ou **Supervised** (les installations « Container » et « Core » n'ont pas d'add-ons). Sinon, gardez le monitoring sur sa propre machine (conteneur Proxmox par exemple) et installez seulement l'intégration ci-dessous.

### Installer l'add-on

1. **Paramètres** → **Modules complémentaires** → **Boutique des modules complémentaires** (en bas à droite).
2. **Trois points** ⋮ en haut à droite → **Dépôts**, collez `https://github.com/Jcpasdutout/ha-monitoring`, cliquez **Ajouter** puis fermez.
3. Rechargez la page, cherchez **Monitoring**, cliquez **Installer** (la construction prend quelques minutes).
4. Activez **Afficher dans la barre latérale**, puis **Démarrer**.
5. Ouvrez **Monitoring** dans la barre latérale et créez le compte administrateur depuis la page **Sondes**.

Pour reprendre les sondes d'une installation existante, voir la documentation de l'add-on (onglet **Documentation**). Avec l'add-on, l'intégration n'a rien à saisir : une fois installée via HACS (étape 2 ci-dessous) et Home Assistant redémarré, **Paramètres** → **Appareils et services** propose « Monitoring » dans **Découverts**. Cliquez **Ajouter** puis **Valider**, et passez les étapes 1 et 3.

## Prérequis

- Le monitoring en **version 2.1 ou plus récente** (celle qui propose les jetons d'accès).
- Home Assistant **2025.8 ou plus récent**, avec [HACS](https://hacs.xyz) installé.

## Installation

### 1. Créer un jeton d'accès dans le monitoring

1. Ouvrez le monitoring (par exemple `http://192.168.1.241:8080`) et connectez-vous (page **Sondes**).
2. En haut à droite, cliquez sur votre identifiant, puis **Jetons d'accès (Home Assistant)**.
3. Laissez le nom « Home Assistant » et cliquez **Créer**.
4. Cliquez **Copier** (ou sélectionnez le jeton qui commence par `mon_`) : il ne sera **plus jamais affiché**. Gardez la fenêtre ouverte le temps de l'étape 3.

Le jeton permet seulement de lire l'état des sondes et de les relancer. Il ne permet pas de modifier les sondes. Pour couper l'accès, supprimez-le depuis la même fenêtre.

### 2. Installer l'intégration avec HACS

1. Dans Home Assistant, ouvrez **HACS** (menu de gauche).
2. En haut à droite, cliquez sur les **trois points** ⋮ puis **Dépôts personnalisés** (*Custom repositories*).
3. Dans **Dépôt**, collez `https://github.com/jcpasdutout/ha-monitoring`, et dans **Type**, choisissez **Intégration**. Cliquez **Ajouter**, puis fermez la fenêtre.
4. Cherchez **Monitoring** dans HACS, ouvrez-le et cliquez **Télécharger** (en bas à droite), puis confirmez.
5. **Redémarrez Home Assistant** : **Paramètres** → **Système** → bouton marche/arrêt en haut à droite → **Redémarrer Home Assistant**.

### 3. Ajouter l'intégration

1. **Paramètres** → **Appareils et services** → **Ajouter une intégration** (en bas à droite).
2. Cherchez **Monitoring** et cliquez dessus.
3. Remplissez :
   - **Adresse du monitoring** : `http://192.168.1.241:8080` (l'adresse que vous tapez dans le navigateur), ou `http://127.0.0.1:8080` avec l'add-on ;
   - **Jeton d'accès** : collez le jeton de l'étape 1.
4. Validez : les appareils et entités apparaissent tout de suite.

## Réglages

Sur la carte de l'intégration (**Paramètres** → **Appareils et services** → **Monitoring**) :

- **Configurer** : fréquence de mise à jour (30 s par défaut ; les sondes gardent leur propre rythme dans le monitoring) et affichage de l'expéditeur et de l'objet des derniers mails.
- ⋮ → **Reconfigurer** : à utiliser si l'**adresse IP du monitoring change** (son conteneur est en DHCP). Laissez le jeton vide pour garder l'actuel.
- Si le jeton est supprimé dans le monitoring, Home Assistant affiche une notification **Réauthentification requise** : créez un nouveau jeton et collez-le.

Les sondes elles-mêmes se gèrent toujours dans la page **Sondes** du monitoring.

## Exemples d'automatisations

Notification quand une sonde passe en erreur ou en alerte :

```yaml
alias: Monitoring - prévenir en cas de problème
triggers:
  - trigger: state
    entity_id: binary_sensor.monitoring_probleme_sur_une_sonde
    to: "on"
    for: "00:02:00"
actions:
  - action: notify.notify
    data:
      title: Monitoring
      message: >
        Problème sur : {{ state_attr('binary_sensor.monitoring_probleme_sur_une_sonde', 'sondes') | join(', ') }}
```

Annonce d'un nouveau mail (remplacez `sensor.boite_free_mails_non_lus` par votre capteur) :

```yaml
alias: Monitoring - nouveau mail
triggers:
  - trigger: state
    entity_id: sensor.boite_free_mails_non_lus
conditions:
  - condition: template
    value_template: "{{ trigger.to_state.state | int(0) > trigger.from_state.state | int(0) }}"
actions:
  - action: notify.notify
    data:
      title: Nouveau mail
      message: >
        {% set m = state_attr('sensor.boite_free_mails_non_lus', 'derniers_mails') %}
        {{ m[0].de ~ ' : ' ~ m[0].objet if m else trigger.to_state.state ~ ' non lus' }}
```

Afficher le tableau de bord complet dans Home Assistant : ajoutez à un tableau de bord une carte **Page web** avec l'adresse du monitoring.

## Dépannage

- **« Impossible de joindre le monitoring »** : vérifiez l'adresse dans un navigateur depuis le même réseau que Home Assistant.
- **« Cette adresse ne répond pas comme le monitoring »** : le monitoring n'est pas encore en version 2.1 ; mettez-le à jour.
- **« Jeton refusé »** : recopiez le jeton en entier, ou créez-en un nouveau.
- Journaux détaillés : **Paramètres** → **Appareils et services** → **Monitoring** → ⋮ → **Activer la journalisation de débogage**.

## Développement

```sh
python -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt
pytest
```
