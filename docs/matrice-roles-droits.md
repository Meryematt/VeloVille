# Matrice rôles x droits

## Droits par route

✅ = autorisé ; sinon, code HTTP renvoyé en cas de refus.

| Route | Anonyme | Exploitant | Direction |
|---|---|---|---|
| `GET /sante` | ✅ | ✅ | ✅ |
| `POST /auth/login` | ✅ | ✅ | ✅ |
| `GET /stations` | 401 | ✅ | ✅ |
| `GET /stations/{station_id}` | 401 | ✅ | ✅ |
| `GET /trajets` | 401 | ✅ | ✅ |
| `GET /incidents` | 401 | ✅ | ✅ |
| `PUT /incidents/{incident_id}/statut` | 401 | ✅ | 403 |
| `GET /indicateurs/activite-par-jour` | 401 | ✅ | ✅ |
| `GET /indicateurs/stations-actives` | 401 | ✅ | ✅ |
| `GET /indicateurs/incidents-par-statut` | 401 | ✅ | ✅ |

- **401** : pas de jeton, ou jeton invalide ou expiré.
- **403** : l'utilisateur est connecté mais son rôle ne permet pas l'action
  (`{"detail": "Acces reserve au role exploitant"}`).

Dans le front, la section de changement de statut d'un incident n'est
affichée qu'à l'exploitant.

## Données sensibles

**Mots de passe** : ils ne sont jamais stockés en clair, seulement leur
hachage bcrypt. En cas d'échec de connexion, le message est le même pour un
identifiant inconnu et pour un mauvais mot de passe.

**Jeton JWT** : il est signé avec `JWT_SECRET` et expire au bout de
`JWT_EXPIRATION_MINUTES`. Un jeton modifié ou expiré est refusé (401). Dans
le front, il est gardé dans `st.session_state` : il n'apparaît ni à l'écran
ni dans l'URL.

**`usager_ref`** : c'est un pseudonyme fourni par la billettique, aucune
donnée directement identifiante n'est importée. Aucun écran du front
n'affiche les trajets, et l'API `GET /trajets` le renvoie vide (`null`) au
rôle direction ; seul l'exploitant le voit, à des fins de support.

**Secrets de configuration** (`JWT_SECRET`, `DATABASE_URL`) : ils sont dans
le fichier `.env`, ignoré par Git. Le fichier `.env.example`, versionné, ne
contient aucune valeur sensible.
