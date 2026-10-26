# **AI/ML Engineer: 7-Day Sprint Framework**

Day 1 is entirely for understanding and notes — a shallow read of every topic in the reference tables below, written straight into the Notes column as you go. Day 2 onward builds the project and goes deep on each one as you hit it.

| Day | Focus | What you ship |
| :---- | :---- | :---- |
| 1 | Scope the project, set up repo \+ CLAUDE.md/AGENT.md, read every topic in the reference tables below and write your own notes for each, design the architecture | A scoped project, a working repo, and written notes on everything you'll need |
| 2 | Embeddings & vector DB setup, build the ingestion → chunking → retrieval pipeline | A working retrieval layer |
| 3 | MCP/tool-calling basics, build the core generation/agent logic, handle context & memory | A working end-to-end response loop |
| 4 | Wrap it in an API, add one guardrail, build a 10–20 case eval set, learn LLM evaluation concepts | A callable API with a guardrail and an eval set |
| 5 | Containerize, deploy to a free-tier host, set up CI/CD, split dev/prod environments | A live, deployed project |
| 6 | Add basic logging, fix bugs, re-run your eval set, reread your Day 1 notes on the Know-tier topics | A monitored, polished project and sharp recall of the theory |
| 7 | Write your project narrative, prep answers for every "know it" topic, rehearse out loud | Your pitch, ready to deliver |

## **Reference: AI-Assisted Development Workflow**

| Priority | Topic | This week | Link | My notes |
| :---- | :---- | :---- | :---- | :---- |
| Build | Context files (CLAUDE.md / AGENT.md) | Write one for your project repo on Day 1; refine it as you go | — | A plain markdown file Claude Code auto-reads every session from the project root, carrying project "why" and conventions so you don't re-explain them each time. |
| Build | Prompting techniques (few-shot, chain-of-thought, system prompts) | Practice on your actual project prompts; keep 2–3 you iterated on | [Anthropic's courses](https://github.com/anthropics/courses) | System prompts set persistent rules, few-shot shows example input→output pairs, chain-of-thought asks the model to reason step by step — together: rules + shape + reasoning. |
| Build | Plan mode | Use it before every multi-file change you make this week | — | AI proposes a no-code plan for a multi-file change and waits for approval, so a wrong assumption costs one correction instead of rework across several files. |
| Build | Debugging with AI | Keep one real example: your prompt, the AI's fix, your judgment call | — | Give the real error/stack trace, ask why it happens (not just "fix it"), and judge the proposed fix rather than accepting it blindly. |
| Build | Where you rely on AI code vs. step in | Notice this as a habit while building — don't study it separately | — | Let AI drive boilerplate and well-specified mechanical tasks; step in yourself for architecture, security-sensitive code, and anything you need to defend in the interview. |

## **Reference: Foundations**

| Priority | Topic | This week | Link | My notes |
| :---- | :---- | :---- | :---- | :---- |
| Know | Python / data structures & algorithms | Skip fresh study this week — you'll exercise it while building | — | Skip fresh study — exercised while building; be ready to explain the Big-O of your own data-structure choices (dict O(1) lookup vs. list O(n) scan). |
| Know | Core ML basics (train/val/test, overfitting, bias-variance) | One short refresher on Day 1 — recognize the terms, don't derive them | — | Train on the training set, tune on validation, get an honest score from an untouched test set; overfitting = memorizes noise (high train, low val); bias-variance = too simple vs. too sensitive to training data. |
| Know | Evaluation metrics (precision, recall, F1, confusion matrix) | Pick one metric for your Day 4 eval set and understand it well | — | Precision = of what you flagged, how much was right (few false alarms); recall = of what was actually right, how much you caught (few misses); F1 balances both — pick based on which error costs more. |
| Know | Transformer/LLM basics (tokenization, embeddings, attention) | One good visual explainer on Day 1 | [The Illustrated Transformer](http://jalammar.github.io/illustrated-transformer/) | Text → tokens → embeddings (vector, similar meaning = closer) → attention (each token weighs every other token) → next-token prediction; embeddings power retrieval, attention is why the LLM can use retrieved context. |

## **Reference: LLM & RAG Systems**

| Priority | Topic | This week | Link | My notes |
| :---- | :---- | :---- | :---- | :---- |
| Build | Context window & memory | Implement the minimum your project's conversation flow actually needs | — | Context window = max tokens per call (input+output), shared by system prompt, history, retrieved chunks, and the question; "memory" is engineering you build (sliding window, summarization), not a model feature. |
| Build | RAG: the retrieve-then-generate loop | Build it directly on Day 2 — the fastest way to actually understand it | [RAG explained](https://www.pinecone.io/learn/retrieval-augmented-generation/) | Embed query → retrieve top-k nearest chunks → augment prompt with them → generate a grounded answer; retrieval quality is a hard ceiling on answer quality, so debug retrieval first. |
| Build | Embeddings & vector databases | Use one free option (Chroma) rather than reading theory first | [Chroma docs](https://docs.trychroma.com/getting-started) | An embedding model turns text into a vector where similar meaning = closer position; Chroma does fast approximate-nearest-neighbor search, defaulting to L2 distance unless you set it to cosine — cosine is the more common choice for text embeddings. |
| Build | Chunking & retrieval strategy | Tune chunk size/overlap once retrieval looks wrong — you'll learn it by fixing it | — | Chunk because a whole-doc embedding is a blurry average; too-small chunks lose context, too-large dilute it; overlap keeps boundary ideas intact; tune chunk size/top-k empirically against observed retrieval failures. |
| Build | MCP (Model Context Protocol) | One small tool call is enough this week — it's a differentiator, not a deep dive | [MCP course](https://www.deeplearning.ai/short-courses/mcp-build-rich-context-ai-apps-with-anthropic) | An open standard for exposing tools to LLMs in one consistent format any MCP client can call — like a USB-C connector for AI tool integrations, vs. tool calling which is the general capability itself. |
| Build | Tool calling & agent orchestration | Wire in 2–3 tools your agent can call and route between | [Anthropic's courses](https://github.com/anthropics/courses) | The model outputs a structured call request, your code executes the real function and feeds the result back; orchestration is the think→act→observe loop your code runs while the model decides inside it. |

## **Reference: Serving, Optimization & Evaluation**

| Priority | Topic | This week | Link | My notes |
| :---- | :---- | :---- | :---- | :---- |
| Know | Fine-tuning landscape (LoRA / QLoRA / PEFT) | Know when it beats RAG or better prompting — you won't fine-tune this week | — | Fine-tuning bakes behavior into the model's weights; LoRA/QLoRA are cheap, parameter-efficient ways to do it. Default order: prompting → RAG → fine-tuning only as a last resort when knowledge is stable and format must be very consistent. |
| Know | Quantization & vLLM | One pass on the precision-for-speed/memory tradeoff and why vLLM is fast | [vLLM docs](https://docs.vllm.ai/) | Quantization stores weights in lower precision for less memory and faster inference at some quality cost; vLLM is fast mainly due to PagedAttention (OS-style paged KV cache) plus continuous batching to keep the GPU busy. |
| Know | Inference optimization (Triton, ONNX) | One sentence ready: what a model server does, why ONNX speeds up CPU inference | — | A model server (Triton) handles batching/routing/resource management so app code doesn't run the model directly; ONNX is a framework-agnostic export format that speeds up CPU inference via graph optimizations. |
| Build | LLM evaluation (hallucination, eval harness, LLM-as-judge) | Your Day 4 eval set IS this topic — build it, don't just read about it | [Prompt evaluations course](https://github.com/anthropics/courses) | Hallucination/faithfulness = output not actually supported by the retrieved context, even if it sounds right; an eval harness is a fixed test set you re-run after every change; LLM-as-judge scores output against a rubric since manual grading doesn't scale, but needs spot-checking itself. |

## **Reference: Production Engineering**

| Priority | Topic | This week | Link | My notes |
| :---- | :---- | :---- | :---- | :---- |
| Build | Git/GitHub workflow (PRs, review, branching) | Use feature branches and real PR descriptions all week, even solo | — | Branch per feature keeps main deployable; write real PR descriptions even solo — forces clarity and leaves a trail for the Day 7 narrative. |
| Build | Containerization & deployment | Dockerize and deploy on Day 5 — this is the proof of "shipped" | [Docker get started](https://docs.docker.com/get-started/) | Docker packages the app + all its dependencies into one portable image that runs identically anywhere, fixing "works on my machine"; deployed = that image running continuously at a public URL. |
| Build | One cloud platform (AWS / GCP / Azure) | Pick one free tier and deploy your project there on Day 5 | — | Cloud platforms rent compute/storage on demand instead of managing physical servers; same categories across providers (EC2/Compute Engine/VMs, Lambda/Cloud Functions/Azure Functions). This project uses a free-tier host (Render/Fly.io/Railway) for the fastest path to a public URL. |
| Build | CI/CD (concepts) | One GitHub Actions workflow that runs tests on push is enough | [GitHub Actions quickstart](https://docs.github.com/en/actions/quickstart) | CI = automatically running tests/build on every push to catch problems immediately; CD = continuous delivery (human triggers deploy) or continuous deployment (fully automatic). One workflow running the eval set on push is this week's target. |
| Build | Environments (dev/staging/UAT/prod) | A dev/prod split via environment variables is enough for this project | — | Dev/staging/prod isolate stages of a change; environment variables (not a separate codebase) are the mechanism — a dev/prod split via .env locally and platform-set vars in production is enough this week. |
| Build | Guardrails (prompt injection, PII redaction, output filtering) | Add one real guardrail on Day 4 and be ready to explain it | — | Checks layered around the model call that enforce what prompting can only request — prompt injection defends against malicious instructions hidden in retrieved content, PII redaction masks personal info before logging, output filtering checks the model's output before the user sees it. |
| Build | Observability (logging, drift detection, feedback loops) | Add basic logging on Day 6 — enough to describe what you'd monitor live | — | Logging records what happened per request (query, retrieved chunks, answer, latency, errors); drift detection watches for silent shifts in inputs/outputs over time; feedback loops capture real usage signal to improve the system beyond the static eval set. |
| Know | Data governance | Know the basics: access control, retention, consent | — | Access control (least privilege), retention (don't keep data longer than needed), consent (was data used for what people agreed to) — "I'd add these before real users" is a complete answer without implementing them. |
| Know | Basic SQL | Only if your project needs a database — otherwise skip this week | — | Standard query patterns (SELECT/WHERE/JOIN/GROUP BY) for relational data; this project uses Chroma (a vector DB), not a relational DB, so it isn't needed this week. |

## **The Pitch: Your Interview Narrative**

This is what you'll actually say out loud. Fill in your own answers as you build — Day 7 is for writing this out in full.

| Beat | What to cover | Your answer |
| :---- | :---- | :---- |
| Problem & domain | Who has this problem, how painful is it, why now | *(fill in)* |
| Why AI | Why an LLM beats a simpler non-AI approach here | *(fill in)* |
| Solution design | Architecture, serving mode, deployment mode, success criteria, monitoring | *(fill in)* |
| Your role & workflow | What you scoped/decided yourself vs. what AI generated, plus one concrete debugging example | *(fill in)* |
| Outcome & next steps | What worked, what you'd improve with more time | *(fill in)* |