from datasets import load_from_disk
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model
import torch

MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"

# Load dataset
dataset = load_from_disk(
    "models/optimization_llm/data/hf_dataset"
)

# Tokenizer
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True,
)

tokenizer.pad_token = tokenizer.eos_token


# Convert dataset format -> training text
def format_example(example):
    return {
        "text": (
            f"Instruction: {example['instruction']}\n\n"
            f"Input: {example['input']}\n\n"
            f"Response: {example['output']}"
        )
    }


dataset = dataset.map(format_example)


# Tokenization
def tokenize(example):
    return tokenizer(
        example["text"],
        truncation=True,
        max_length=512,
    )


dataset = dataset.map(
    tokenize,
    remove_columns=dataset.column_names,
)

# Base model
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.bfloat16,
)

# LoRA config
config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=[
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
    ],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

model = get_peft_model(model, config)

# Training args
args = TrainingArguments(
    output_dir="models/optimization_llm/output",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    num_train_epochs=1,
    logging_steps=10,
    save_strategy="epoch",
    bf16=True,
)

# Trainer
trainer = Trainer(
    model=model,
    args=args,
    train_dataset=dataset,
    data_collator=DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    ),
)

# Train
print("Model device:", next(model.parameters()).device)
trainer.train()

# Save adapter
model.save_pretrained(
    "models/optimization_llm/output/final_adapter"
)
