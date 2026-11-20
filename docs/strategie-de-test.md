# Stratégie de test — MiniShop

> Modèle à compléter pendant l'Atelier 12. Une stratégie de test tient sur 2 pages : si elle est plus longue, personne ne la lit.

## 1. Périmètre et risques
| Zone | Risque métier | Probabilité | Impact | Niveau de test principal |
|---|---|---|---|---|
| Calcul des prix (`pricing.py`) | Mauvais montant facturé | Moyenne | Élevé | Unitaire + génération IA |
| API commandes | Commande perdue | Faible | Élevé | API + contrat |
| Interface | Parcours bloqué | Moyenne | Moyen | E2E + visuel |
| Performance | Abandon de panier | … | … | Charge (Locust/JMeter) |
| Sécurité | Fuite / injection | … | … | SAST, SCA, DAST (ZAP) |

## 2. Pyramide et quality gates
| Étape pipeline | Tests | Seuil bloquant |
|---|---|---|
| PR | lint, unitaires, API | 100 % OK, couverture ≥ 85 % |
| main | + E2E, visuel, sécurité | 0 vulnérabilité HIGH/CRITICAL |
| nocturne | charge, ZAP complet | p95 < 300 ms, erreurs < 1 % |

## 3. Règles pour les tests générés par IA

### Relecture et responsabilité
- Tout test généré doit être relu avant fusion par l'auteur de la proposition de modification.
- Un test généré doit être marqué par `@pytest.mark.generated` ou appartenir à un fichier marqué `pytestmark = [pytest.mark.generated, pytest.mark.unit]`.
- L'utilisation d'un LLM ne transfère aucune responsabilité à l'outil : l'auteur de la PR reste responsable des tests qu'il propose.
- Le relecteur vérifie que chaque test correspond à une règle métier, utilise une donnée valide et contient une assertion pertinente.
- Les tests trop permissifs, sans assert utile ou liés uniquement à une implémentation interne peuvent être corrigés ou supprimés.

### Validation avant fusion
- Le test doit compiler, passer sur le code original et échouer lorsqu'une règle métier qu'il vérifie est cassée.
- Les montants financiers doivent être comparés avec `decimal.Decimal`, jamais avec des float.
- Les exceptions attendues doivent être précises : type d'erreur, puis message si la règle le précise.
- Les cas générés doivent être testés par mutation ; les mutants survivants doivent être analysés pour identifier les règles non protégées.
- Les règles ajoutées uniquement par le modèle doivent être validées par l'équipe métier ou par la spécification avant conservation.
- Toute divergence entre la spécification et le code doit être documentée avec `# DIVERGENCE SPEC/CODE : ...` puis décidée avant fusion.

### Secrets et données sensibles
- Les prompts ne doivent jamais contenir de mot de passe, jeton, clé API, secret d'environnement ou donnée client réelle.
- Les produits, commandes, comptes et journaux envoyés au modèle doivent être fictifs ou anonymisés.
- La spécification et le code source peuvent être envoyés à un fournisseur IA uniquement après vérification qu'ils ne contiennent aucune donnée confidentielle.

### Traitement des résultats
- Bug applicatif confirmé : corriger le code et conserver le test qui détecte la régression.
- Hallucination du modèle : rejeter ou corriger le test et améliorer le prompt si nécessaire.
- Divergence non tranchée : suspendre la fusion et demander une décision métier avant toute correction automatique.
- Test trop large ou trop permissif : préciser les assertions, le type d'exception ou le message attendu.

## 4. Gestion des tests instables (flaky)
- Détection : `ai_tools/test_history.py` (score ≥ 0,6).
- Quarantaine : marqueur `flaky`, ticket ouvert, délai de correction 5 jours.

## 5. Indicateurs suivis
Taux de réussite sur main, durée de la suite, nombre de tests flaky, couverture, MTTR d'une régression.
