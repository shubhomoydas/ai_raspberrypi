import os
import re
import traceback
from io import BytesIO, FileIO
import json as jsonlib
from pprint import pprint, pformat
import datetime
import requests
from requests.adapters import HTTPAdapter
from buildhat import Motor
import sounddevice as sd
from scipy.io.wavfile import write
import wavio as wv
from openai import OpenAI


API_URL = os.getenv("CLAUDE_API_URL")  # "https://api.anthropic.com/v1/messages"
API_KEY = os.getenv("CLAUDE_API_KEY")  # "<api_key>"
API_VER = os.getenv("CLAUDE_API_VER")  # "2023-06-01"

cache = {}


def get_url_response(url, method="GET", headers=None, params=None, json=None, data=None,
                     max_timeout=30, network_timeout=7):
    resp = err_message = None
    try:
        req = requests.Session()
        req.mount(url, HTTPAdapter(max_retries=2))
        if method == "GET":
            resp = req.get(url, headers=headers, params=params, timeout=network_timeout)
        elif method == "POST":
            resp = req.post(url, headers=headers, params=params, json=json, data=data, timeout=network_timeout)
        elif method == "DELETE":
            resp = req.delete(url, headers=headers, timeout=network_timeout)
        else:
            raise ValueError(f"invalid method {method}")
    except Exception as e:
        err_message = traceback.format_exc()
        pprint(err_message)
        raise e
    if not (200 <= resp.status_code < 300):
        print(
            f"Response (status_code: {resp.status_code}) headers in error: {resp.headers.get('Content-Type', '')}"
        )
        if resp.headers and "application/json" in resp.headers.get('Content-Type', ''):
            ret_status, ret_resp = resp.status_code, resp.json()
        else:
            ret_status, ret_resp = resp.status_code, resp.text
    elif "application/json" in resp.headers.get('Content-Type', ''):
        resp_json = None
        if resp.status_code == 200:
            resp_json = resp.json()
        ret_status, ret_resp = resp.status_code, resp_json
    else:
        ret_status, ret_resp = resp.status_code, resp
    return ret_status, ret_resp


def get_http_headers(api_key=None, api_ver=None):
    headers = {"content-type": "application/json"}
    headers["x-api-key"] = f"{api_key}"
    headers["anthropic-version"] = f"{api_ver}"
    return headers


def call_http_endpoint(data=None, url=None, api_key=None, api_ver=None, method="POST"):
    url = url or self.url
    api_key = api_key or self.api_key
    headers = get_http_headers(api_key=api_key, api_ver=api_ver)
    status, resp = get_url_response(url=url, method=method,
                                    headers=headers, json=data,
                                    max_timeout=30,
                                    network_timeout=30)
    return status, resp


def call_completion_endpoint(prompt, model=None, temperature=0.0,
                             max_tokens=1024) -> dict:
    data = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if isinstance(prompt, list):
        data["messages"] = prompt
    status, completion = call_http_endpoint(data=data, url=API_URL, api_key=API_KEY, api_ver=API_VER, method="POST")
    content = None
    if ("content" in completion and len(completion["content"]) > 0
            and isinstance(completion["content"][0], dict)
            and "text" in completion["content"][0]):
        content = completion["content"][0].get("text")
        if content:
            content = content.strip()
    usage_ = completion.get("usage")
    usage = None
    if usage_:
        usage = dict(resp_tokens=usage_["output_tokens"],
                     prompt_tokens=usage_["input_tokens"],
                     total_tokens=usage_["output_tokens"] + usage_["input_tokens"])
    return content, usage, completion


def get_completion(prompt, model="claude-3-5-sonnet-20241022", cache=None):
    content = usage = completion = None
    if cache is not None and (val := cache.get(prompt)):
        if val:
            content = val.get("content")
            usage = val.get("usage")
            completion = val.get("completion")
        return content, usage, completion
    prompt_messages = [{"role": "user", "content": prompt}]
    content, usage, completion = call_completion_endpoint(prompt=prompt_messages, model=model)
    if cache is not None:
        cache[prompt] = dict(content=content, usage=usage, completion=completion)
    return content, usage, completion


instructions = """
You are an agent that translates tasks expressed in english natural language to tool APIs.
The available tool APIs to operate motors are provided below. When an input text is provided 
as a task in triple back-ticks, you will determine a sequence of steps that will 
perform that task. The steps have the following format:

<format>

Task: the input task you must perform
Thought: you should always think about what to do.
Action: The `Action` output must be a well-formed JSON with no linebreaks and with the attribute `name` \
having the tool name (must be one of the tools provided) and its required parameters as other attributes of the JSON.
Observation: the result of the action. This will only come from the users and must not be present in the output.
... (this Thought/Action/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

</format>

The final answer must be prefixed with 'Final Answer:'

The `Task` will be provided and you should not output this. You may output only the \
`Thought`, `Action`, and `Final Answer` if applicable for the next step, and wait \
for the user to provide the `Observation` in case it is needed. You cannot output \
the `Observation` because it is not within your control and can only be provided by \
the user.

When determining the `Action`, you must abide by the following points:
  1. The `Action` must be a well-formed JSON that identifies the tool by the attribute `name`.
  2. If no tool is available to satisfy a step required by the task, then the `Action` must be \
output as a JSON with a attribute `error` which has the message `no tool applicable`.
  3. The JSON must be formatted to be on a single line without any line breaks.
  4. The parameters for the tool identified for `Action` are defined by the tool definitions \
provided below and should be output as part of the JSON.
  5. Whenever a tool expects a `blocking` parameter, it should be set as `False` by default unless \
its value is explicitly specified by the task.
  6. Whenever a tool expects the `speed` parameter, it should be set as 50 by default unless explicitly \
specified by the task.
  7. When the task requires going `forwards` or turning `right`, the speed should be a positive value.
  8. If no direction of movement is mentioned, then a `forward` movement is assumed.
  9. When the task requires going `backwards` or turning `left`, the speed should have a negative value.
  10. If no direction of movement is mentioned, then a `forward` movement is assumed.
  11. Tasks that require turning `right` or `left` imply turn by 90 or -90 degrees as appropriate. \
  12. Values of all numerical parameters such as `degrees`, `speed`, `rotations`, \
`seconds` must be integers.

IMPORTANT: Even though the `Observation` is part of the step format, you must never output the `Observation`.

<tools>

Tool1:
Name: run_for_degrees
Description: Runs the motor for N degrees. Speed of 1 means 1 revolution / second. \
This is the preferred tool to go forwards or backwards or turn left or right.
Parameters:
    degrees: Number of degrees to rotate
    speed: Speed ranging from -100 to 100
    blocking: Whether call should block till finished.


Tool2:
Name: run_for_rotations
Description: Run motor for N rotations.
Parameters:
    rotations: Number of rotations
    speed: Speed ranging from -100 to 100
    blocking: Whether call should block till finished


Tool3:
Name: run_for_seconds
Description: Run motor for N seconds.
Parameters:
    seconds: Time in seconds
    speed: Speed ranging from -100 to 100
    blocking: Whether call should block till finished


Tool4:
Name: run_to_position
Description: Run motor to position (in degrees).
Parameters:
    degrees: Position in degrees from -180 to 180
    speed: Speed ranging from 0 to 100
    blocking: Whether call should block till finished
    direction: shortest (default)/clockwise/anticlockwise


Tool5:
Name: set_default_speed
Description: Set the default speed of the motor.
Parameters:
    default_speed: Speed ranging from -100 to 100


Tool6:
Name: start
Description: Start motor.
Parameters:
    speed: Speed ranging from -100 to 100


Tool7:
Name: stop
Description: Stop motor.

</tools>


Begin! Output the next steps's `Thought`, `Action`, and `Final Answer` (if applicable).
Task: ```{task}```

{thought_actions}

"""


model = "claude-3-5-sonnet-20241022"
# prompt = [{"role": "user", "content": "Hello, world"}]

# prompt = [{"role": "user", "content": "Hello, world"}]

# iins = instructions.format(instruction="Turn right")
# prompt = [{"role": "user", "content": iins}]

# content, usage, completion = call_completion_endpoint(prompt=prompt, model=model)
# pprint(content)


BEGIN_KEY = re.compile(r'^\s*(Thought|Action|Observation|Final Answer)\s*:', flags=re.MULTILINE|re.IGNORECASE)


def skip_char(text, char):
    if not text:
        return text
    pos = text.find(char)
    if pos >= 0:
        return text[(pos + 1):]
    return text


def parse_thought_action_list(text, first_only=True):
    # print(f"Parsing:\n{text}")
    iter = BEGIN_KEY.finditer(text)
    values = []
    prev_key = None
    prev_pos = 0
    for m in iter:
        pos = m.start()
        if prev_key is not None:
            values.append(dict(key=prev_key, value=skip_char(text[prev_pos:pos], ":").strip()))
        key = m.group(1)
        prev_key = key
        prev_pos = pos
    if prev_key is not None:
        values.append(dict(key=prev_key, value=skip_char(text[prev_pos:], ":").strip()))
    # pprint(values)
    if first_only:
        new_values = []
        found = set()
        for v in values:
            key = v.get("key")
            val = v.get("value")
            if key not in found:
                found.add(key)
                new_values.append(v)
        values = new_values
    return values


def parse_thought_action(text):
    parsed = parse_thought_action_list(text)
    action_found = False
    ta = {}
    for item in parsed:
        key = item.get("key")
        value = item.get("value")
        if action_found and key in ["Thought", "Action", "Observation", "Final Answer"]:
            break
        elif key in ["Observation"]:
            continue
        elif key == "Action" and value:
            action_found = True
        ta[key] = value
    return ta


def format_messages(messages):
    if not messages:
        return ""
    mlist = []
    for message in messages:
        for k in ["Thought", "Action", "Observation", "Final Answer"]:
            if k in message:
                mlist.append(f"{k}: {message.get(k)}")
    if not mlist:
        return ""
    return("\n\n".join(mlist))


def make_f(name):
    def tf(**args):
        return f"invoked tool {name} with {args}"
    return tf


class DummyMotor:
    def __init__(self):
        self.run_for_degrees = make_f("run_for_degrees")
        self.run_for_rotations = make_f("run_for_rotations executed successfully")
        self.run_for_seconds = make_f("run_for_seconds executed successfully")
        self.run_to_position = make_f("run_to_position executed successfully")
        self.set_default_speed = make_f("set_default_speed executed successfully")
        self.start = make_f("start executed successfully")
        self.stop = make_f("stop executed successfully")


def prepare_motor_funcs(motor_a):
    funcs = {
        "run_for_degrees": {"f": motor_a.run_for_degrees, "params": {"degrees", "speed", "blocking"}},
        "run_for_rotations": {"f": motor_a.run_for_rotations, "params": {"rotations", "speed", "blocking"}},
        "run_for_seconds": {"f": motor_a.run_for_seconds, "params": {"seconds", "speed", "blocking"}},
        "run_to_position": {"f": motor_a.run_to_position, "params": {"degrees", "speed", "blocking", "direction"}},
        "set_default_speed": {"f": motor_a.set_default_speed, "params": {"default_speed"}},
        "start": {"f": motor_a.start, "params": {"speed"}},
        "stop": {"f": motor_a.stop, "params": {}},
    }
    return funcs


def get_motor_funcs(dummy=False):
    if dummy:
        motor = DummyMotor()
    else:
        motor = Motor('A')
    return motor, prepare_motor_funcs(motor)


def invoke_tool(d, funcs):
    name = d.get("name")
    if not name or name not in funcs:
        print(f"Invalid name: {name}")
    f_def = funcs.get(name)
    f = f_def.get("f")
    all_params = f_def.get("params")
    params = {k: v for k, v in d.items() if k in all_params}
    observation = None
    try:
        f(**params)
        observation = f"Executed tool {name} with {params}"
    except Exception as e:
        print(e)
        pprint(d)
        observation = f"Failed to execute tool {name}"
    return observation


def messages_to_steps(messages):
    steps = []
    answer = None
    if not messages:
        return steps, answer
    is_error = False
    for message in messages:
        if (action := message.get("Action")) and isinstance(action, str):
            try:
                action = jsonlib.loads(action)
                thought_action = {"Action": action, "Thought": message.get("Thought")}
                steps.append(thought_action)
            except Exception as e:
                print(f"Error in parsing action: {e}")
                is_error = True
                break
        else:
            if answer := message.get("Final Answer"):
                # print(f"Final answer: {answer}")
                break
    return steps, answer


def get_action_steps(task, funcs):
    steps = []
    answer = messages = None
    if not task:
        print(f"No task given: {task}")
    else:
        messages = []
        for i in range(10):
            fmessages = format_messages(messages)
            if False and messages:
                print(f"Formatted messages>>>>>:\n{fmessages}\n=========")
            prompt = instructions.format(task=task, thought_actions=fmessages)
            content, usage, completion = get_completion(prompt=prompt, model=model, cache=cache)
            if not content:
                print(f"oh, oh! Failed to get response")
                break
            try:
                thought_action = parse_thought_action(content)
                messages.append(thought_action)
                # print("==Thought action==")
                # pprint(thought_action)
                if "Final Answer" in thought_action:
                    break
                if "Action" in thought_action:
                    json_content = jsonlib.loads(thought_action.get("Action"))
                    pprint(json_content)
                    if error := json_content.get("error"):
                        print(error)
                        break
                    observation = invoke_tool(json_content, funcs)
                    thought_action["Observation"] = observation
            except Exception as e:
                print(e)
                print(content)
                break
        if False and messages:
            print(f"Final messages>>>>>:\n{format_messages(messages)}\n=========")
        if messages:
            steps, answer = messages_to_steps(messages)
    return steps, answer, messages
