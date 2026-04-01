# LLM Robustness Evaluation Framework

An automated red-teaming framework for evaluating the safety alignment of large language models. Implements multiple adversarial evaluation strategies based on peer-reviewed research to benchmark LLM robustness.

> **Disclaimer**: This tool is designed for *defensive* security research only. It should only be used against locally deployed open-source models that you own and control.

## Research References

| Strategy | Paper | Venue |
|----------|-------|-------|
| PAIR | Chao et al., *Jailbreaking Black Box LLMs in Twenty Queries* | 2023 |
| Crescendo | Microsoft, *Multi-Turn Jailbreak* | USENIX Security 2025 |
| Many-Shot | Anthropic, *Many-Shot Jailbreaking* | 2024 |
| ArtPrompt | Jiang et al., *ASCII Art-based Jailbreak* | ACL 2024 |

## Setup

```bash
# 1. Install Ollama and pull a target model
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3:8b-instruct

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Run evaluation
python main.py --config configs/default.yaml
```

## Project Structure

```
├── main.py                 # Entry point
├── configs/
│   └── default.yaml        # Experiment configuration
├── core/
│   ├── orchestrator.py     # Attack loop coordinator
│   ├── target.py           # Target model interface (Ollama)
│   └── judge.py            # Response safety evaluator
├── strategies/
│   ├── base.py             # Abstract strategy interface
│   ├── crescendo.py        # Multi-turn escalation (Microsoft)
│   ├── many_shot.py        # Context window flooding (Anthropic)
│   └── art_prompt.py       # ASCII art evasion (ACL 2024)
├── utils/
│   ├── ascii_converter.py  # Sensitive word → ASCII art
│   └── report.py           # Result aggregation & visualization
└── results/                # Experiment outputs
```

## Key Metrics

- **ASR** (Attack Success Rate): % of test cases where the target produced unsafe output
- **Avg Rounds to Break**: Mean conversation turns before alignment failure
- **Strategy Effectiveness**: Per-strategy ASR comparison across models
- **Defense Impact**: ASR reduction after applying input/output filters
