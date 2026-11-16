# Трассировка по этапам

| Этап | Запуск | Не разведено до | Не разведено после | DRC (без шелкографии) |
|---|---|---|---|---|
| init | 1 | — | 300 | hole_clearance 4 |
| power | 1 | 300 | 265 | hole_clearance 4, via_dangling 3 |
| planes | 1 | 265 | 265 | hole_clearance 4, via_dangling 3 |
| fast | 1 | 265 | 248 | hole_clearance 4, via_dangling 4 |
| rest | 1 | 248 | 20 | via_dangling 5, hole_clearance 4 |
