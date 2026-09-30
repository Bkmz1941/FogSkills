if (!UnityEngine.Application.isPlaying) return "не в play";
var d = Cozy.Grid.LevelIO.Load("night_build");
if (d == null) return "нет файла";
Cozy.Grid.GridCursor.I.RestoreLevel(d);
int walls = 0, floors = 0; foreach (var gb in Cozy.Grid.GridBlock.All) { if (gb == null) continue; if (gb.role == Cozy.Grid.GridRole.Wall) walls++; else if (gb.role == Cozy.Grid.GridRole.Floor) floors++; }
return "текущий=" + Cozy.Grid.LevelIO.CurrentLevelName + " стен=" + walls + " плит=" + floors + " объектов=" + Cozy.Grid.InteractiveObject.All.Count + " игрок=" + Cozy.Grid.PlayerRef.GameObject.transform.position.ToString("F2");
