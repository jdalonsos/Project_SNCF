# Project SNCF

Ce document explique de manière complète toutes les étapes nécessaires
pour lancer le projet en local avec Docker.\


------------------------------------------------------------------------

## Étape 1 : Cloner le dépôt Git

La première étape consiste à récupérer le projet depuis GitHub.\
Pour cela, exécutez la commande suivante dans votre terminal :

``` bash
git clone https://github.com/jdalonsos/Project_SNCF.git
```

Une fois le dépôt cloné, entrez dans le dossier du projet :

``` bash
cd Project_SNCF
```

Cela vous place dans le répertoire contenant tous les fichiers
nécessaires au lancement du projet.

------------------------------------------------------------------------

## Étape 2 : Construire l'image Docker du projet

Avant de pouvoir exécuter l'application, vous devez construire son image
Docker.\
Cette image contient l'environnement Python, les dépendances, ainsi que
le code du projet.

Pour la construire, exécutez la commande suivante :

``` bash
docker build -t sncf-app .
```

Cette commande crée une image nommée `sncf-app`.\
Le point (`.`) indique à Docker d'utiliser le Dockerfile présent dans le
dossier courant.

------------------------------------------------------------------------

## Étape 3 : Lancer l'application avec Docker

Une fois l'image construite, vous pouvez lancer l'application dans un
conteneur Docker.\
Utilisez la commande suivante :

``` bash
docker run -p 8501:8501 sncf-app
```

Cette commande :

-   démarre un conteneur basé sur l'image `sncf-app`
-   expose le port interne 8501 du conteneur vers le port 8501 de votre
    machine

------------------------------------------------------------------------

## Accès à l'application

Après le lancement réussi du conteneur, ouvrez un navigateur web et
allez à l'adresse :

    http://localhost:8501

L'interface du projet devrait s'afficher et être entièrement
fonctionnelle.

------------------------------------------------------------------------