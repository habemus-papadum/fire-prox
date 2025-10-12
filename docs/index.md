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
Firestore serves as a powerful primitive for distributed applications. Fire-Prox aims to make Firestore convenient for developing for research workflows.  Examples of applications that Fire-Prox is designed to be useful in are:
- Applications like Alpha Evolve involve a large swarm of AI agents trying to optimize a -specific problem, but that coordinate loosely through a database of successful ideas. 
- Long-running agent flows, think Claude Code, that implement a complicated plan in a step-by-step fashion. 

In both of the examples above, not only do AI agents need a place to write things down, but you also want a system that can let you see what's going on as it's happening, both at a macro scale and also to be able to drill down into hero mode to see exactly what a specific execution thread is doing. Then, also to be able to analyze post hoc to see again in aggregate and in low-level detail so that you can further optimize the system.

Firestore provides such a framework, in particular, given its both Python backend and also the nature of its JavaScript client-side backend. On the client's side, you can have pretty simple to develop web apps that don't need that they can on the one hand use authenticated workloads that don't need a special authentication server or authentication infrastructure. They can just kind of piggyback off of what Firestore provides. And this library tries to revive what seems to be missing, which is a way to quickly interrogate a Firestore database, try to figure out what was going on. Have ad hoc, like create simple throwaway tools that maybe convert data to a data frame, et cetera. So that you have the shims and harnesses you need to build a complicated application, build and test that complicated application. 

