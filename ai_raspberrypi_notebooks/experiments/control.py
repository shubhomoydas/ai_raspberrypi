import os
import json
from pprint import pprint, pformat
from experiments.audio_control import *
from experiments.motor_control import *


def control(real_funcs, dummy_funcs):
    """ Runs an audio input loop

    Args:
        :param real_funcs: dict
            References to motor functions to actually perform the physical actions
        :param dummy_funcs: dict
            References to dummy motor functions that will be used to only generate execution plans
    
    Loops over the following steps:
        1. Prints 'Press [return] to speak, or 'q' to exit: ' and waits for user input
        2. If user inputs `q` in step 1, then program quits
        3. If user presses `[return]` key in setp 1, then program starts recording 4 secs audio
        4. Recorded audio is transcribed to text and the text is set as the task
        5. The transcribed text is converted back to audio and output through speaker; user is asked to confirm the task
        6. If user confirms, a plan is generated for the task (transcribed text)
        7. The plan is executed
        8. Final result of the task is announced through audio speaker
        9. Go to Step 1
    """
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
    dummy_motor, dummy_funcs = get_motor_funcs(dummy=True)
    real_motor, real_funcs = get_motor_funcs(dummy=False)
    
    print(f"Motor connected: {real_motor.connected}")
    
    control(real_funcs, dummy_funcs)
    print("Turning off the motor...")
    real_motor.off()
