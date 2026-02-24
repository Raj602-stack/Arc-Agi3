from arc_agi import Arcade, OperationMode
from arcengine import GameAction

arc = Arcade(
    operation_mode=OperationMode.OFFLINE,
    environments_dir="./environment_files"
)

env = arc.make("pm07-v1", render_mode="terminal")

print(env.action_space)

env.step(GameAction.ACTION1)

print(arc.get_scorecard())
