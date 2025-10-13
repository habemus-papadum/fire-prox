# fire-prox
Prototyping focused acceleration layer for Firestore

## Installation
```bash
pip install fire-prox
```
-------------

## Project Overview

Fire-Prox is a schemaless, state-aware proxy library for Google Cloud Firestore designed to accelerate rapid prototyping. Unlike traditional Object-Document Mappers (ODMs), Fire-Prox embraces dynamic, schema-free development by providing an intuitive, Pythonic interface that reduces boilerplate and aligns with object-oriented programming patterns.

**Key Philosophy**: Fire-Prox is an "anti-ODM" for the prototyping stage, wrapping (not replacing) the official `google-cloud-firestore` library to provide a higher-level abstraction optimized for developer velocity during rapid iteration.

----------------

## Features

Fire-Prox provides a comprehensive feature set for rapid Firestore prototyping, wrapping the native client with an intuitive, Pythonic interface.

### Core Architecture

#### State Machine
Fire-Prox manages documents through a four-state lifecycle that enables lazy loading and safe state management:

```python
# DETACHED - New document, not yet in Firestore
user = users.new()
user.name = 'Ada Lovelace'

# ATTACHED - Linked to Firestore path, but data not loaded
user = db.doc('users/ada')

# LOADED - Full data loaded from Firestore
user.fetch()
print(user.name)

# DELETED - Marked as deleted
user.delete()
```

Check state anytime: `user.is_detached()`, `user.is_loaded()`, `user.is_deleted()`.

#### Dual API (Sync & Async)
Complete synchronous and asynchronous implementations with shared base classes:

```python
# Synchronous API
from fireprox import FireProx
db = FireProx(firestore.Client())
user = db.doc('users/ada')
user.fetch()
user.score += 10
user.save()

# Asynchronous API
from fireprox import AsyncFireProx
async_db = AsyncFireProx(firestore.AsyncClient())
user = async_db.doc('users/ada')
await user.fetch()
user.score += 10
await user.save()
```

**Demo**: [Phase 1 Sync](/demos/phase1/sync/) | [Phase 1 Async](/demos/phase1/async/)

#### Dynamic Schema
Work without predefined schemas or models - pure Python object manipulation:

```python
# No schema definition needed
user = users.new()
user.name = 'Ada'
user.birth_year = 1815
user.tags = ['mathematician', 'programmer']
user.metadata = {'verified': True}
user.save()  # All fields saved automatically
```

### Data Operations

#### Field-Level Dirty Tracking
Fire-Prox tracks exactly which fields changed, enabling efficient partial updates:

```python
user = db.doc('users/ada')
user.fetch()

user.email = 'ada@example.com'
user.bio = 'Pioneer programmer'

print(user.dirty_fields)  # {'email', 'bio'}
user.save()  # Only 2 fields sent to Firestore, not entire document
```

**Performance**: 50-90% bandwidth reduction for typical updates. Lower Firestore costs.

**Demo**: [Phase 2 Features](/demos/phase2/demo/)

#### Post-Hoc Schema Typing
Opt in to stronger static types once a collection stabilizes by attaching a dataclass schema:

```python
from dataclasses import dataclass
from fire_prox import DocRef

@dataclass
class UserProfile:
    display_name: str
    age: int

@dataclass
class Order:
    purchaser: DocRef[UserProfile]
    total: float

users = db.collection("users").with_schema(UserProfile)
orders = db.collection("orders").with_schema(Order)

order_doc = orders.new()
order = order_doc.schema_view()  # IDE hints reflect the dataclass fields
order.purchaser = users.doc("ada")._doc_ref  # treated as DocRef[UserProfile]
order.total = 199.00
order_doc.save()
```

- `with_schema()` binds a dataclass to a collection without changing runtime behaviour.
- `DocRef[T]` marks fields that should hold Firestore references for static analyzers.
- `.schema_view()` offers a strongly typed view for IDEs while retaining FireObject lifecycle methods.
- Static typing fixtures in the test suite run Pyright to guarantee the metadata stays healthy.

#### Atomic Operations
Concurrency-safe operations that execute server-side without read-modify-write conflicts:

```python
# Increment counters safely across multiple clients
post.increment('views', 1)
post.increment('likes', 1)

# Array operations with automatic deduplication
user.array_union('tags', ['python', 'firestore', 'python'])  # No duplicates
user.array_remove('tags', ['deprecated'])

# Combine multiple atomic operations
post.increment('comment_count', 1)
post.array_union('commenters', [user_id])
post.save()  # All operations atomic
```

**Use Cases**: View counters, like buttons, inventory tracking, tag management.

**Demo**: [Phase 2 Features](/demos/phase2/demo/)

#### Subcollections
Organize data hierarchically with nested collections:

```python
# Create subcollection under a document
user = db.doc('users/ada')
posts = user.collection('posts')
post = posts.new()
post.title = 'On the Analytical Engine'
post.year = 1843
post.save()  # Saved to users/ada/posts/{auto-id}

# Nested subcollections (unlimited depth)
comment = post.collection('comments').new()
comment.text = 'Brilliant!'
comment.save()  # users/ada/posts/{id}/comments/{id}
```

**Demo**: [Phase 2 Features](/demos/phase2/demo/)

#### Document References
Automatic conversion between FireObjects and DocumentReferences with lazy loading:

```python
# Assign FireObjects directly - auto-converts to DocumentReference
post.author = user  # user is a FireObject
post.reviewers = [user1, user2, user3]  # Works in lists
post.contributors = {'lead': user1, 'editor': user2}  # And dicts
post.save()

# Read back - references auto-hydrate to FireObjects
post = db.doc('posts/article1')
post.fetch()

# Lazy loading on first access
print(post.author.name)  # Automatically fetches author document
for reviewer in post.reviewers:
    print(reviewer.name)  # Each loads on-demand
```

**Features**: Object identity (same reference = same object), nested support, type safety.

**Demo**: [Document References](/demos/topics/document_references/)

#### Batch Operations
Atomic multi-document writes for efficient bulk operations:

```python
batch = db.batch()

# Accumulate operations (up to 500)
for user_id in user_ids:
    user = db.doc(f'users/{user_id}')
    user.fetch()
    user.status = 'active'
    user.credits = 50
    user.save(batch=batch)  # Queued, not executed yet

# Commit all atomically in single request
batch.commit()  # All succeed or all fail
```

**Performance**: 100x faster for 100 documents (1 round trip vs 100).

**Demo**: [Batch Operations](/demos/topics/batches/)

### Querying & Analytics

#### Query Builder
Chainable, intuitive query interface returning hydrated FireObjects:

```python
# Simple filtering
active_users = users.where('active', '==', True).get()

# Complex queries
top_scorers = (users
    .where('country', '==', 'England')
    .where('birth_year', '>', 1800)
    .order_by('score', direction='DESCENDING')
    .limit(10)
    .get())

for user in top_scorers:
    print(f"{user.name}: {user.score}")  # Fully loaded FireObjects
```

**Features**: All Firestore operators, multiple orderings, immutable query pattern.

**Demo**: [Phase 2.5 Query Builder](/demos/phase2_5/demo/)

#### Pagination
Cursor-based navigation for efficient large dataset traversal:

```python
# Get first page
page1 = users.order_by('created_at').limit(20).get()

# Get next page using cursor
last_created = page1[-1].created_at
page2 = users.order_by('created_at').start_after({'created_at': last_created}).limit(20).get()

# Previous page
first_created = page2[0].created_at
page1_again = users.order_by('created_at').end_before({'created_at': first_created}).limit(20).get()
```

**Methods**: `start_at()`, `start_after()`, `end_at()`, `end_before()`.

**Demo**: [Pagination Patterns](/demos/topics/pagination/)

#### Projections
Field-level query optimization for massive bandwidth savings:

```python
# Select only needed fields
names_only = users.select('name').get()
# Returns: [{'name': 'Ada'}, {'name': 'Grace'}, ...]

# Combine with filtering and sorting
high_earners = (users
    .where('salary', '>', 100000)
    .select('name', 'salary', 'department')
    .order_by('salary', direction='DESCENDING')
    .limit(10)
    .get())

# Returns vanilla dicts, not FireObjects (by design)
for emp in high_earners:
    print(f"{emp['name']}: ${emp['salary']:,}")
```

**Performance**: 50-95% bandwidth reduction for large documents.

**Demo**: [Field Projections](/demos/topics/projections/)

#### Aggregations
Server-side analytics without document transfer - dramatically faster and cheaper:

```python
from fire_prox import Count, Sum, Avg

# Simple aggregations
total_users = users.count()
total_revenue = orders.sum('amount')
avg_rating = products.avg('rating')

# With filtering
active_users = users.where('active', '==', True).count()
dept_payroll = employees.where('dept', '==', 'Engineering').sum('salary')

# Multiple aggregations in one query
stats = employees.aggregate(
    total=Count(),
    payroll=Sum('salary'),
    avg_salary=Avg('salary'),
    avg_age=Avg('age')
)
print(f"Team: {stats['total']}, Payroll: ${stats['payroll']:,}, Avg: ${stats['avg_salary']:,}")
```

**Performance**: 2-10x faster than client-side calculations. Only aggregated results transferred, not documents.

**Demo**: [Aggregations](/demos/topics/aggregations/)

### Advanced Features

#### Transactions
ACID transactions with decorator pattern and automatic retry:

```python
from google.cloud import firestore

transaction = db.transaction()

@firestore.transactional
def transfer_money(transaction, from_id, to_id, amount):
    from_user = db.doc(f'users/{from_id}')
    to_user = db.doc(f'users/{to_id}')

    # Transactional reads
    from_user.fetch(transaction=transaction)
    to_user.fetch(transaction=transaction)

    # Modify and save
    from_user.balance -= amount
    to_user.balance += amount

    from_user.save(transaction=transaction)
    to_user.save(transaction=transaction)

# Automatically retries on conflicts
transfer_money(transaction, 'alice', 'bob', 100)
```

**Features**: Read-modify-write atomicity, automatic retry, works with atomic operations.

**Demo**: [Transactions](/demos/topics/transactions/)

#### Real-time Listeners
Live updates via `on_snapshot()` for reactive applications:

```python
# Sync callback
def on_user_change(docs, changes, read_time):
    for doc in docs:
        print(f"User updated: {doc.name}")

unsubscribe = users.where('active', '==', True).on_snapshot(on_user_change)

# Async handler
async def on_user_change_async(docs, changes, read_time):
    for doc in docs:
        print(f"User updated: {doc.name}")
        await process_update(doc)

unsubscribe = await users.on_snapshot(on_user_change_async)

# Stop listening
unsubscribe()
```

**Features**: Document and collection listeners, sync and async handlers, change types (added/modified/removed).

**Demo**: [Real-time Listeners](/demos/topics/on_snapshot/)

#### Vector Embeddings
Semantic search integration with Firestore's vector capabilities:

```python
from fire_prox import FireVector

# Store embeddings
doc.embedding = FireVector([0.1, 0.2, 0.3, ...])  # Your embedding vector
doc.save()

# Vector search (using native Firestore vector search)
# See demo notebook for full examples with actual embedding models
```

**Use Cases**: Semantic search, recommendation systems, similarity matching.

**Demo**: [Vector Embeddings](/demos/topics/vector_embeddings/)

#### Native Query Integration
Seamlessly mix Fire-Prox with native Firestore API when needed:

```python
from google.cloud.firestore_v1.base_query import Or, FieldFilter

# Complex query with native API
native_query = client.collection('users').where(
    filter=Or([
        FieldFilter('country', '==', 'England'),
        FieldFilter('country', '==', 'USA')
    ])
)

# Hydrate results to FireObjects
users = [FireObject.from_snapshot(snap) for snap in native_query.stream()]

# Now use Fire-Prox features on these objects
for user in users:
    user.last_accessed = firestore.SERVER_TIMESTAMP
    user.save()  # Partial updates, dirty tracking, etc.
```

**Philosophy**: Fire-Prox wraps, not replaces. Use native API when needed, Fire-Prox when convenient.

### Additional Features

**Timestamp Handling**: Automatic timezone support and SERVER_TIMESTAMP integration. [Demo](/demos/topics/dates_and_timestamps/)

**Error Messages**: Clear, actionable error messages with state information for debugging.

**Type Safety**: Comprehensive type hints for IDE support and static analysis.

**Test Harness**: Built-in testing utilities for Firebase emulator integration. 

## Use Cases
Firestore serves as a powerful primitive for distributed applications. Fire-Prox makes Firestore convenient for research workflows and rapid prototyping. Example applications where Fire-Prox excels:

- **Multi-agent systems** like Alpha Evolve, where large swarms of AI agents optimize specific problems while coordinating loosely through a shared database of successful ideas
- **Long-running agent workflows** (such as Claude Code) that implement complex plans in a step-by-step fashion

In both scenarios, AI agents need persistent storage, but you also need observability: the ability to monitor what's happening in real-time at both macro and micro scales, drill down into specific execution threads, and analyze results post-hoc in aggregate and granular detail to optimize the system.

Firestore provides an ideal framework for this, offering both Python and JavaScript clients. On the client side, you can build web applications that leverage Firestore's built-in authentication without requiring separate authentication infrastructure. Fire-Prox fills the missing piece: making it easy to quickly interrogate your Firestore database, create ad-hoc analysis tools, convert data to DataFrames, and build the shims and harnesses needed to develop and test complex distributed applications. 

In addition to the agentic applications above, `fire-prox` might be also useful for the following: 

- Implementing a distributed queue large portion of the semantics available with AWS SQS queues. 
- An Airflow-like distributed task graph executor. 

##  Target Audience
If you understand Firestore and are excited by the myriad of cool applications you could build with it, but wish that interacting with it in Python was a little bit easier, then Fire-Prox is might be a good library for you. 

On the other hand, if you already have an application and you need some storage for your objects, and you think that Firestore might be a good solution, then this may not be the right fit. Firestore is pretty close to letting you think of it as a distributed dictionary or list, but you will likely fight with it a little bit because it comes with certain constraints.  That's not a big deal. It's worth the effort, but I'm not sure it's worth compounding that fight by using a proxy layer, which will just make the errors more opaque. Also, if you're about to build something, but you have a very clear plan about what you're going to build and it's just a matter of delivery, then there are other Python libraries that are proper object-document mappers that work well with schemas that you have already worked out in advance. 

Understanding Firestore is sort of critical. This library provides convenience but doesn't try to simplify or relieve the user from understanding the semantics and details of Firestore. With that said, if you're not that familiar with Firestore, you can look through the demos starting with phase 1, phase 2, and phase 3, and then proceed to the topics. You'll sort of see how the library was built up step-by-step, and that's a pretty good way to not only understand the library in a digestible format, but also get some exposure to various Firestore topics. Unfortunately, the Firestore Python SDK's documentation isn't very strong. It's much easier to learn about Firestore by reading about the documentation in `JavaScript`.  One issue with the `JavaScript` is has features and semantics that are important on client-side devices that might have limited connectivity.  This provides it with a certain amount of magic. For instance, in the browser, you typically don't await an operation in Firestore that ends up effectively blocking. Whereas if you use the "sync" version, the control flow continues in a way that is actualy async, however the local state reflects the impact of your operation but can be rolled back if something happens when it's finally persisted to the database. This magic doesn't exist in the Python and other server-oriented SDKs. But that's a bit of a digression. Good luck!  


## Why AI?
`fire-prox` has been almost entirely written by AI agents. The development process involves dictating prompts and having AI agents handle implementation, testing, and documentation.

The workflow typically begins with creating an architecture document. For this project, I consulted multiple leading AI systems—Gemini, GPT, and Claude—to evaluate different architectural approaches before selecting the most promising design. From there, AI agents implement features incrementally, following the architectural blueprint.

This approach has proven remarkably effective. AI-assisted development enables consistent quality throughout the project by eliminating the natural fatigue that comes with extensive coding sessions. Rather than managing implementation details, I focus on architecture, design decisions, and quality oversight. The result is comprehensive test coverage, detailed documentation, and cleaner code than would typically emerge from a rushed implementation.

More broadly, this project serves as an exploration of AI-assisted software development. The tools have matured to where they can handle complex, multi-phase projects with proper scaffolding—good test infrastructure, clear architecture documents, and iterative validation. The development velocity is substantial, but more importantly, the consistency of output quality remains high across all phases. For prototyping and research tools where iteration speed matters, AI-assisted development offers a compelling approach worth exploring. 

