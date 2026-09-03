# Production Release Graph

A product release may include mobile, web, API, workers, databases and infrastructure. V3 models component dependencies, deploy order, rollback order and migration constraints as one release graph.

Destructive or backward-incompatible migrations require explicit safety evidence. Old deployed clients that still consume a changed field block the normalized migration assessment.
