from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import torch

BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"
ADAPTER_PATH = "models/optimization_llm/output/final_adapter"

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.bfloat16,
)

model = PeftModel.from_pretrained(
    base_model,
    ADAPTER_PATH,
)

model.eval()


def recommend_action(
    primary_use,
    square_feet,
    meter_reading,
    air_temperature,
):
    prompt = f"""
Instruction: Recommend an energy optimization action.

Input:
{{
 "primary_use":"{primary_use}",
 "square_feet":{square_feet},
 "meter_reading":{meter_reading},
 "air_temperature":{air_temperature}
}}

Response:
"""

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
    )

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=80,
            do_sample=False,
        )

    return tokenizer.decode(
        outputs[0],
        skip_special_tokens=True,
    )
