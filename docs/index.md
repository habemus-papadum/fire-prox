# fire-prox
Prototyping focused acceleration layer for Firestor

## Installation
```bash
pip install fire-prox
```
-------------

## Project Overview

Fire-Prox is a schemaless, state-aware proxy library for Google Cloud Firestore designed to accelerate rapid prototyping. Unlike traditional Object-Document Mappers (ODMs), Fire-Prox embraces dynamic, schema-free development by providing an intuitive, Pythonic interface that reduces boilerplate and aligns with object-oriented programming patterns.

**Key Philosophy**: Fire-Prox is an "anti-ODM" for the prototyping stage, wrapping (not replacing) the official `google-cloud-firestore` library to provide a higher-level abstraction optimized for developer velocity during rapid iteration.

----------------

## Use Cases
Firestore serves as a powerful primitive for distributed applications. Fire-Prox makes Firestore convenient for research workflows and rapid prototyping. Example applications where Fire-Prox excels:

- **Multi-agent systems** like Alpha Evolve, where large swarms of AI agents optimize specific problems while coordinating loosely through a shared database of successful ideas
- **Long-running agent workflows** (such as Claude Code) that implement complex plans in a step-by-step fashion

In both scenarios, AI agents need persistent storage, but you also need observability: the ability to monitor what's happening in real-time at both macro and micro scales, drill down into specific execution threads, and analyze results post-hoc in aggregate and granular detail to optimize the system.

Firestore provides an ideal framework for this, offering both Python and JavaScript clients. On the client side, you can build web applications that leverage Firestore's built-in authentication without requiring separate authentication infrastructure. Fire-Prox fills the missing piece: making it easy to quickly interrogate your Firestore database, create ad-hoc analysis tools, convert data to DataFrames, and build the shims and harnesses needed to develop and test complex distributed applications. 

## Features
**TODO**: Add a comprehensive list of supported features, highlighting feature parity with the native Firestore client. Include links to demos, and provide code snippets demonstrating how each feature works. 

## Why AI?
`fire-prox` has been almost entirely written by AI agents. The development process involves dictating prompts and having AI agents handle implementation, testing, and documentation.

The workflow typically begins with creating an architecture document. For this project, I consulted multiple leading AI systems—Gemini, GPT, and Claude—to evaluate different architectural approaches before selecting the most promising design. From there, AI agents implement features incrementally, following the architectural blueprint.

This approach has proven remarkably effective. AI-assisted development enables consistent quality throughout the project by eliminating the natural fatigue that comes with extensive coding sessions. Rather than managing implementation details, I focus on architecture, design decisions, and quality oversight. The result is comprehensive test coverage, detailed documentation, and cleaner code than would typically emerge from a rushed implementation.

More broadly, this project serves as an exploration of AI-assisted software development. The tools have matured to where they can handle complex, multi-phase projects with proper scaffolding—good test infrastructure, clear architecture documents, and iterative validation. The development velocity is substantial, but more importantly, the consistency of output quality remains high across all phases. For prototyping and research tools where iteration speed matters, AI-assisted development offers a compelling approach worth exploring. 

