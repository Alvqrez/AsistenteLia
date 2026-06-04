"""
skills — Habilidades de Lia, auto-registradas (Fase 3).

Cada módulo define una o más subclases de `core.skill.Skill`. El
`SkillRegistry` recorre este paquete al arrancar, instancia cada skill y
registra sus `IntentSpec` en el `IntentRouter`. Añadir una habilidad nueva =
crear un archivo aquí; no se toca el núcleo.

Las skills NO reimplementan lógica: delegan en los servicios ya probados
(`mod_sistema`, `mod_dev`, `mod_internet`, ...) a través del AssistantContext.
Así la rearquitectura cambia la ORQUESTACIÓN sin alterar el comportamiento.

Los módulos cuyo nombre empieza por '_' son helpers, no skills.
"""
