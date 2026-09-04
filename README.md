# Sobry Energy pour Home Assistant

[![Ouvrir ce dépôt dans HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=atomtoto&repository=Sobry_HACS&category=integration)

Intégration Home Assistant qui récupère les prix de l'électricité **Sobry** et
les expose sous forme de capteurs (prix actuel, prix suivant, min, max, moyenne)
pour piloter vos automatisations et suivre vos coûts.

## Installation

### Avec le bouton (le plus simple)

1. Cliquez sur le bouton bleu ci-dessus, puis sur **Télécharger**.
2. Redémarrez Home Assistant.
3. Allez dans **Paramètres** → **Appareils et services** → **Ajouter une
   intégration** et cherchez **Sobry Energy**.

### Manuellement

Si le bouton ne fonctionne pas (HACS non installé, instance non accessible) :

1. **HACS** → menu ⋮ → **Dépôts personnalisés**
2. Ajoutez `https://github.com/atomtoto/Sobry_HACS` avec la catégorie
   **Integration**
3. Installez **Sobry Energy**, puis reprenez aux étapes 2 et 3 ci-dessus.

## Configuration

Tout se règle depuis l'interface, à l'ajout de l'intégration puis à tout moment
via **Configurer**. Aucune modification de `configuration.yaml` n'est nécessaire.

| Option | À quoi ça sert | Valeurs |
| --- | --- | --- |
| **Segment** | Type de raccordement. `C5` pour un particulier ou un petit professionnel (≤ 36 kVA), `C4` au-delà. | `C5`, `C4` |
| **Option TURPE** | Option tarifaire d'acheminement, indiquée sur votre contrat ou votre facture. | `CU`, `CU4`, `MU4`, `MUDT`, `LU` (`CU` et `LU` seulement en `C4`) |
| **Profil** | Particulier ou professionnel. | `particulier`, `pro` |
| **Affichage** | Prix TTC ou hors taxes, pour le mode sans clé API. | `TTC`, `HT` |
| **Granularité** | Pas de temps des prix. | `quarter_hourly` (15 min), `hourly` (1 h) |
| **Mode de taxe** | Prix TTC ou hors taxes, pour le mode avec clé API. | `ttc`, `ht` |
| **Clé API Sobry** | Facultative. Voir [Prix personnalisés](#prix-personnalisés-avec-clé-api). | vide par défaut |

En segment `C4`, le profil `pro` et l'affichage `HT` sont appliqués
automatiquement.

Dans le doute, laissez les valeurs par défaut : elles correspondent à un
particulier au tarif le plus courant.

## Capteurs créés

Les prix sont exprimés en **€/kWh** et rafraîchis toutes les **15 minutes**.

| Capteur | Description |
| --- | --- |
| `sensor.sobry_current_price` | Prix en cours |
| `sensor.sobry_next_price` | Prix de la période suivante |
| `sensor.sobry_min_price` | Prix le plus bas de la période récupérée |
| `sensor.sobry_max_price` | Prix le plus haut de la période récupérée |
| `sensor.sobry_average_price` | Prix moyen de la période récupérée |

Le capteur *prix en cours* porte en plus des attributs utiles, dont
`all_prices` : la liste complète des prix à venir, pratique pour tracer une
courbe (carte ApexCharts par exemple) ou chercher le meilleur créneau.

### Exemple d'automatisation

Lancer le lave-linge quand le prix passe sous 0,15 €/kWh :

```yaml
automation:
  - alias: "Lave-linge aux heures pas chères"
    trigger:
      - platform: numeric_state
        entity_id: sensor.sobry_current_price
        below: 0.15
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.prise_lave_linge
```

## Prix personnalisés (avec clé API)

Par défaut, l'intégration utilise les prix publics Sobry correspondant aux
options choisies ci-dessus.

Si vous renseignez une **clé API Sobry**, elle interroge à la place votre compte
et renvoie les prix de *votre* contrat. Les options Segment, TURPE, Profil et
Affichage ne sont alors plus utilisées : seules la Granularité et le Mode de
taxe s'appliquent.

Pour l'activer : **Paramètres** → **Appareils et services** → **Sobry Energy** →
**Configurer** → collez votre clé, puis validez.

## Dépannage

- **Les capteurs sont `indisponible` peu après l'ajout** : consultez
  **Paramètres** → **Système** → **Journaux**. Le message indique la cause
  (clé API invalide, quota atteint, API injoignable). L'intégration retente
  automatiquement au rafraîchissement suivant.
- **`clé API invalide`** : vérifiez la clé dans votre compte Sobry et
  recollez-la sans espace avant/après.
- **L'icône Sobry ne s'affiche pas** : voir ci-dessous.
- **Autre problème** : ouvrez un ticket sur
  [le suivi des tickets](https://github.com/atomtoto/Sobry_HACS/issues), en
  joignant l'extrait de journal correspondant.

## Icône de l'intégration

Les images de marque sont fournies dans `custom_components/sobry/brand/`.
Home Assistant 2026.3 et ultérieur les charge directement depuis le dossier de
l'intégration.

Sur les versions antérieures, Home Assistant ne lit les icônes que depuis le
dépôt [home-assistant/brands](https://github.com/home-assistant/brands) : une
intégration personnalisée y reste sans icône tant que ses images n'y ont pas été
soumises dans `custom_integrations/sobry/`.
