import os
import json
from pprint import pprint, pformat
from experiments.audio_control import *
from experiments.motor_control import *


dummy_motor, dummy_funcs = get_motor_funcs(dummy=True)
real_motor, real_funcs = get_motor_funcs(dummy=False)

print(f"Motor connected: {real_motor.connected}")


def control():
    answer = None
    for i in range(5):
        inp = input("Press [return] to speak, or 'q' to exit: ")
        
        if inp.lower().startswith("q"):
            print("'q' pressed... Exiting")
            break
        
        byte_stream = get_audio_instruction(duration=4)
        task = transcribe(byte_stream)
        print(f"\nTask: {task}\n")
        if True:
            audio = speak(f"You said: {task}. Is that correct?")
            confirm = input("[y/n]: ")
            if not(confirm.lower() == "y"):
                continue
            else:
                print("proceeding with operating motor...")
        thought_actions, answer, messages = get_action_steps(task, funcs=dummy_funcs)
        for thought_action in thought_actions:
            thought = thought_action.get("Thought")
            step = thought_action.get("Action")
            print(f"\nThought: {thought}")
            print(f"Action: {step}\n")
            if not (error := step.get("error")):
                obs = invoke_tool(step, real_funcs)
                # obs = invoke_tool(step, dummy_funcs)
            else:
                print(f"Error in executing step: {error}")
        
        if answer:
            print(f"Final answer: {answer}")
            audio = speak(answer)


if __name__ == '__main__':
    control()
    print("Turning off the motor...")
    real_motor.off()
