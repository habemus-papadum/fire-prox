

# **FireProx: An Architectural Blueprint for a Dynamic Firestore Prototyping Library**

## **I. Introduction: The FireProx Philosophy \- A Toolkit for Rapid Prototyping**

### **A. The Problem: Prototyping Friction with the Native API**

Google Cloud Firestore offers a powerful, scalable, and strongly consistent NoSQL database, accessible in Python through the google-cloud-firestore client library.1 This official library provides a comprehensive and explicit interface for all of Firestore's capabilities, making it a robust foundation for production applications. However, for developers in the rapid prototyping and iterative phases of a project, this very explicitness can introduce significant friction, slowing down the creative cycle.

The standard workflow for basic operations involves multiple, verbose steps. To read a document, a developer must first create a DocumentReference, call the .get() method to retrieve a DocumentSnapshot object, and then invoke the .to\_dict() method to finally access the data as a standard Python dictionary.3 Similarly, creating or updating a document requires manually constructing a dictionary of data to pass to the .set() or .update() methods. Path construction for nested documents and subcollections relies on string-based paths, such as client.collection('users').document('user\_id').collection('posts'), which are prone to typographical errors and become cumbersome as the data model deepens.5

This API design, while appropriate for a low-level client library focused on control and clarity, imposes a cognitive tax on the developer. The boilerplate code required for common create, read, update, and delete (CRUD) operations distracts from the primary task of implementing and testing application logic. This creates a conceptual "impedance mismatch" between the developer's mental model, which is often object-oriented (user.name \= 'new\_name'), and the library's required interaction model, which is dictionary-centric (user\_ref.update({'name': 'new\_name'})). The goal of the FireProx library is to bridge this gap, providing a more intuitive, Pythonic layer that accelerates development velocity by minimizing boilerplate and aligning the programming interface with the developer's object-oriented thought process.

### **B. The Solution: A Schemaless, State-Aware Proxy**

FireProx is proposed as a schemaless, state-aware proxy library built atop the official google-cloud-firestore client. Its design philosophy is a direct response to the needs of rapid prototyping, where data models are fluid and strict schemas are an impediment rather than a benefit. This positions it as a distinct alternative to the prevailing trend in the Python-Firestore ecosystem.

Currently, many available libraries are Object-Document Mappers (ODMs), such as firestore-pydantic-odm 6, firestore-odm 7, and firestore.8 These tools bring the discipline of schema enforcement to Firestore, often using classes and type hints to define the structure of documents. This approach is invaluable for production environments where data integrity and validation are paramount. However, the user's request explicitly rejects this model, highlighting an underserved niche: developers in the exploratory phase of a project. During this stage, the freedom to dynamically add, remove, and restructure fields without predefined schemas is critical for rapid iteration.

FireProx embraces this need for flexibility. It is not an ODM but rather an "anti-ODM" for the prototyping stage. Its core value proposition is not rigidity but dynamism. It achieves this through a central proxy object that allows for on-the-fly attribute creation and modification, behaving much like a Python namespace. This object is also intelligent, maintaining an internal state that tracks its connection to the upstream Firestore database and whether its local data has been modified. This state-aware design enables a host of powerful features, from lazy-loading of data to automatic, efficient partial updates, all while presenting a clean, object-oriented facade to the developer.

## **II. Core Architecture: The FireObject Proxy**

### **A. The FireObject Class: A Unified Interface**

The central component of the FireProx library is the FireObject class. This class serves as a versatile proxy, capable of representing a Firestore document in various states throughout its lifecycle. It is designed to be the single, unified interface through which developers interact with documents, whether they exist only in local memory or are synchronized with the remote database.

Internally, a FireObject instance will manage two primary pieces of state:

1. A google.cloud.firestore\_v1.document.DocumentReference object, which will be stored once the FireObject is "attached" to a specific path in the Firestore database. This reference is the bridge to the underlying native library.4  
2. An internal dictionary, referred to as \_data, which serves as a local cache for the document's fields. All dynamic attribute access will read from and write to this cache.

This dual-component design allows the FireObject to cleanly separate its identity (the path in Firestore) from its content (the data fields), which is the key to its flexible state management.

### **B. The FireObject Internal State Machine**

The intelligence of the FireObject lies in its internal state machine. This mechanism governs the object's behavior, dictating how it responds to method calls and attribute access based on its current status relative to the remote Firestore document. This design provides a powerful abstraction over the inherent asynchronicity and latency of network operations. For example, it allows a developer to work with a reference to a remote object (ATTACHED state) without incurring the immediate performance penalty of a network request to fetch its data. The library defers this operation until the data is actually needed, a pattern known as lazy loading, which is seamlessly managed by the state machine.

The FireObject can exist in one of four distinct states:

1. **DETACHED**: The object exists purely in Python memory. It has no corresponding document in Firestore, and its internal DocumentReference is None. This is the initial state for new documents created locally. By definition, a DETACHED object is considered "dirty," as all of its data is new and unsaved.  
2. **ATTACHED**: The object is linked to a specific document path in Firestore and holds a valid DocumentReference. However, its local \_data cache is empty, as the document's contents have not yet been fetched from the server. Any attempt to access a data attribute on an ATTACHED object will automatically trigger a data fetch, transitioning it to the LOADED state.  
3. **LOADED**: This is the primary operational state. The object is linked to a Firestore document, and its data has been successfully fetched from the server and populated into the local \_data cache. The object is now a full, in-memory representation of the remote document, ready for reading and modification.  
4. **DELETED**: The object represents a document that has been successfully deleted from Firestore. It retains its last known ID and path for reference but is marked as defunct to prevent further modification or save attempts.

The transitions between these states are governed by specific API calls, as detailed in the following table.

| Current State | Action (Method Call) | Parameters | Next State | Side Effects (Firestore API Call) |
| :---- | :---- | :---- | :---- | :---- |
| (N/A) | FireObject(path) | path to existing doc | ATTACHED | None |
| (N/A) | collection.new() | None | DETACHED | None |
| DETACHED | .save() | Optional doc\_id | LOADED | document.create() or document.set() |
| ATTACHED | .fetch() | None | LOADED | document.get() |
| ATTACHED | \_\_getattr\_\_(name) | Attribute name | LOADED | document.get() (triggered implicitly) |
| LOADED | .fetch() | None | LOADED | document.get() (refreshes data) |
| LOADED | \_\_setattr\_\_(name, val) | Attribute name, value | LOADED | None (marks object as dirty) |
| LOADED | .save() | None | LOADED | document.update() (if dirty) or No-op |
| LOADED | .delete() | None | DELETED | document.delete() |

### **C. Dynamic Attribute Handling via Python's Data Model**

To achieve the desired schemaless, namespace-like behavior, the FireObject will leverage Python's special data model methods to intercept attribute access. This allows it to proxy attribute operations to its internal \_data dictionary, creating a seamless experience for the developer.

* **\_\_getattr\_\_(self, name)**: This method is invoked when an attribute is accessed that is not found in the object's standard \_\_dict\_\_. The FireObject implementation will first check its internal \_data cache for a key matching name.  
  * If the key exists, its value is returned.  
  * If the key does not exist and the object is in the ATTACHED state, this method will first trigger a .fetch() operation. This transitions the state to LOADED and populates the \_data cache. It then re-attempts the lookup.  
  * If the attribute still does not exist after the fetch, a standard AttributeError is raised.  
* **\_\_setattr\_\_(self, name, value)**: This method intercepts all attribute assignments. The implementation will differentiate between internal control attributes (e.g., \_data, \_state) and public data attributes. For data attributes, instead of setting the attribute on the instance itself, it will perform two actions:  
  1. Update the \_data dictionary with the new key-value pair: self.\_data\[name\] \= value.  
  2. Add the attribute name to an internal \_dirty\_fields set. This set is the core mechanism for tracking which fields have been modified, enabling efficient partial updates when .save() is called.  
     This method will also be responsible for wrapping any incoming dictionaries or lists into their respective proxy types (ProxiedMap, ProxiedList), which is detailed in Section IV.  
* **\_\_delattr\_\_(self, name)**: This method will handle attribute deletion. It will remove the key name from the \_data dictionary and add the field to the \_dirty\_fields set, marking it for removal from the remote document on the next save.

## **III. The Developer API: Syntax and Usage Patterns**

### **A. Object Lifecycle Management**

The FireProx API is designed to be intuitive and to significantly reduce the boilerplate associated with the native google-cloud-firestore library. The following table provides a direct comparison of the syntax for common operations, highlighting the gains in simplicity and conciseness.

| Operation | Native google-cloud-firestore Syntax | FireProx Syntax |
| :---- | :---- | :---- |
| **Create Doc (Auto-ID)** | doc\_ref \= client.collection('users').document() doc\_ref.set({'name': 'Ada', 'year': 1815}) | user \= users\_collection.new() user.name \= 'Ada' user.year \= 1815 await user.save() |
| **Create Doc (Custom ID)** | doc\_ref \= client.collection('users').document('alovelace') doc\_ref.set({'name': 'Ada', 'year': 1815}) | user \= users\_collection.new() user.name \= 'Ada' user.year \= 1815 await user.save(doc\_id='alovelace') |
| **Read Document** | doc\_ref \= client.collection('users').document('alovelace') doc \= doc\_ref.get() if doc.exists: name \= doc.to\_dict()\['name'\] | user \= db.doc('users/alovelace') name \= user.name (lazy loads) |
| **Update Single Field** | doc\_ref \= client.collection('users').document('alovelace') doc\_ref.update({'year': 1816}) | user \= db.doc('users/alovelace') user.year \= 1816 await user.save() |
| **Update Nested Field** | doc\_ref \= client.collection('users').document('alovelace') doc\_ref.update({'location.city': 'London'}) | user \= db.doc('users/alovelace') user.location\['city'\] \= 'London' await user.save() |
| **Delete Document** | client.collection('users').document('alovelace').delete() | user \= db.doc('users/alovelace') await user.delete() |

### **B. State Inspection**

To provide transparency into the object's lifecycle, the FireObject will expose a set of simple boolean properties and methods for inspecting its current state.

* user.state: Returns a state enum value (e.g., State.LOADED, State.DETACHED).  
* user.is\_loaded(): Returns True if the object's state is LOADED, False otherwise.  
* user.is\_attached(): Returns True if the object has a DocumentReference (i.e., is in any state other than DETACHED).  
* user.is\_dirty(): Returns True if any fields have been modified since the last fetch or save operation.  
* user.is\_deleted(): Returns True if the object's state is DELETED.

### **C. Working with Subcollections**

Accessing subcollections will be handled through an intuitive, chainable API that mirrors Firestore's conceptual data model. The native API's reliance on string concatenation or repeated method calls (.collection().document().collection()) can obscure the hierarchical relationship between documents and their subcollections.5 FireProx will improve upon this by making subcollections accessible as methods on a parent FireObject instance. This reinforces the parent-child relationship in code, making it more readable and less error-prone.

**Proposed FireProx Syntax:**

Python

\# Get a reference to a parent document  
user \= db.doc('users/alovelace')

\# Access its 'posts' subcollection  
posts\_collection \= user.collection('posts')

\# Create a new document within that subcollection  
new\_post \= posts\_collection.new()  
new\_post.title \= "Analysis of the Analytical Engine"  
new\_post.published\_year \= 1843  
await new\_post.save()

### **D. Querying and Hydration**

FireProx will provide a lightweight, chainable query builder for common query scenarios. However, a more critical feature for ensuring the library's long-term viability is its ability to integrate with the native query engine. The native google-cloud-firestore library is continually evolving, with new, powerful query capabilities such as OR queries being added over time.9 It would be impractical and brittle for FireProx to attempt to wrap every possible query feature.

Instead, the library will adopt the "escape hatch" principle. It will provide a simple query interface for the most common use cases, but it will also offer a seamless way for developers to execute complex queries using the native API and then "hydrate" the results into convenient FireObject instances. This design ensures that developers are never trapped by the limitations of the FireProx query builder and can always leverage the full power of the underlying library when needed.

**Lightweight Querying Example:**

Python

users\_collection \= db.collection('users')

\# Chainable query builder  
query \= users\_collection.where('birth\_year', '\>', 1800).order\_by('birth\_year').limit(10)

\# Asynchronously execute the query and iterate over FireObject instances  
async for user in await query.get():  
    print(f"{user.name} (born {user.birth\_year})")

**Hydration from Native Queries Example:**

Python

from google.cloud.firestore\_v1.base\_query import FieldFilter

\# 1\. Use the powerful native query API for complex queries  
native\_query \= client.collection('users').where(  
    filter\=FieldFilter('birth\_year', '==', 1815)  
)  
native\_docs\_stream \= native\_query.stream()

\# 2\. Use the FireProx 'from\_snapshot' class method to hydrate results  
fire\_objects \= \[FireObject.from\_snapshot(snap) for snap in native\_docs\_stream\]

\# fire\_objects is now a list of fully functional, LOADED FireObject instances

### **E. Seamless Document Reference Handling**

FireProx will abstract away the complexity of handling Firestore's Reference data type, allowing developers to work with linked documents as if they were nested objects.12 This is achieved through a bidirectional translation layer within the FireObject.

**Writing References:** When a developer assigns one FireObject instance as an attribute of another, the library will automatically detect this. Instead of storing the object itself, it will extract the underlying DocumentReference and save that to Firestore. This maintains the correct data model without requiring the developer to manually manage reference objects.12

Python

\# Assume 'author\_obj' is a loaded FireObject for 'users/alovelace'  
author\_obj \= db.doc('users/alovelace')

\# Create a new post and assign the author object directly  
post \= db.collection('posts').new()  
post.title \= "On the Mechanical Execution of Computation"  
post.author \= author\_obj  \# FireProx translates this to a DocumentReference

await post.save()   
\# The 'author' field in the saved Firestore document is a Reference type

**Reading and Auto-Hydrating References:** Conversely, when a FireObject is loaded from Firestore, any fields of the Reference data type are automatically converted into new FireObject instances in the ATTACHED state. These objects are "lazy"; they do not fetch their own data until one of their attributes is accessed for the first time.14 This prevents unnecessary database reads while providing an intuitive, "dot-notation" syntax for traversing document relationships.

Python

\# Fetch a post that has a reference to an author  
post \= db.doc('posts/some-post-id')

\# Accessing '.author' returns a new FireObject in the ATTACHED state.  
\# No database read has occurred for the author yet.  
author\_ref \= post.author 

\# Accessing '.name' on the author object triggers an automatic fetch  
\# for that document's data.  
print(f"Post by: {author\_ref.name}") \# Fetches 'users/alovelace' data here

This auto-hydration mechanism provides the convenience of an object graph while respecting Firestore's model of shallow queries, where related documents are only fetched on demand.14

## **IV. Advanced Internals: Transparent Mutation Tracking**

### **A. The ProxiedMap and ProxiedList**

A key challenge in providing a seamless object-oriented interface is tracking mutations within nested data structures like dictionaries (maps) and lists (arrays). If a developer modifies a nested value, such as user.settings\['notifications'\].append('email'), the parent FireObject must be aware of this change to correctly mark itself as dirty.

FireProx will solve this by implementing two special container classes: ProxiedMap and ProxiedList. These classes will inherit from Python's abstract base classes collections.abc.MutableMapping and collections.abc.MutableSequence, respectively, ensuring they behave exactly like standard dict and list objects.

When a dictionary or list is assigned to a FireObject attribute, it will be transparently wrapped in one of these proxy containers. The proxy container is initialized with a reference to its parent FireObject and the key path to its own location within the parent's data structure (e.g., ('settings', 'notifications')).

Any method that mutates the container's state—such as \_\_setitem\_\_, \_\_delitem\_\_, append, extend, pop, or sort—will be overridden. The overridden method will first perform its standard operation (e.g., append the item to the internal list) and then immediately call a private \_mark\_dirty(path) method on its parent FireObject. This ensures that any modification, no matter how deeply nested, correctly propagates a "dirty" signal up to the root object.

This mechanism also allows the library to translate idiomatic Python operations into optimized, atomic Firestore updates. The native API provides special operators like ArrayUnion and ArrayRemove for modifying arrays without reading and rewriting the entire array.10 When a developer calls .append() on a ProxiedList, the proxy can record this specific action. Upon saving, the parent FireObject can analyze these recorded actions and construct an efficient firestore.ArrayUnion(\[...\]) update rather than sending the entire modified list, resulting in better performance and lower cost.

### **B. Recursive Proxying and Firestore Constraint Enforcement**

This proxying mechanism will be applied recursively. When a new dictionary or list is added to an existing ProxiedMap or ProxiedList, it will also be automatically wrapped in a new proxy container. This ensures that mutation tracking works flawlessly at any level of nesting.

Furthermore, these proxy containers provide an ideal location to enforce Firestore's own constraints, shifting error detection from a remote runtime failure to an immediate, local development-time exception. Firestore imposes several limitations, such as a maximum nesting depth for maps and restrictions on characters in field names.11

Without FireProx, a developer might inadvertently create a data structure that violates these rules, only discovering the error when the .set() or .update() call fails on the server. This can make debugging difficult. With FireProx, the ProxiedMap's \_\_setitem\_\_ method can check the current nesting depth before adding a new sub-map. If the operation would exceed Firestore's limit, it can immediately raise a ValueError with a clear error message. This "fail-fast" approach provides immediate feedback to the developer, dramatically improving the development experience and reducing time spent debugging data structure issues.

## **V. Integration and Configuration**

### **A. Client Initialization and Management**

FireProx is designed as a wrapper, not a replacement. As such, it will not attempt to manage credentials or client configuration. This is a complex and security-critical area that the official Google Cloud libraries handle robustly. The Google Cloud client can be authenticated in numerous ways, such as via the GOOGLE\_APPLICATION\_CREDENTIALS environment variable, service account JSON files, or automatic credential discovery within Google Cloud environments like App Engine or Cloud Functions.3

By delegating this responsibility, FireProx avoids reinventing a complex and sensitive component. This design reduces the library's maintenance burden and attack surface, and it ensures that any future improvements or security updates to the official client's authentication mechanisms are automatically available to FireProx users.

The initialization process will be straightforward. The developer will first configure and instantiate the standard google.cloud.firestore.Client and then pass that instance to the main FireProx entry point class.

**Proposed Initialization Syntax:**

Python

from google.cloud import firestore  
from fireprox import FireProx

\# 1\. Standard Google Cloud authentication and client initialization  
\#    This can be done in any way supported by the official library.  
native\_client \= firestore.Client(project='my-project-id')

\# 2\. Initialize the FireProx library with the pre-configured native client  
db \= FireProx(native\_client)

\# 3\. Start using the simplified FireProx API  
user \= db.doc('users/alovelace')
print(user.name)

### **B. Dual API: Synchronous and Asynchronous Support**

The official google-cloud-firestore library provides two distinct client flavors: `firestore.Client` for synchronous operations and `firestore.AsyncClient` for asynchronous operations. To provide maximum flexibility, **FireProx supports both paradigms through parallel implementations**:

* **Synchronous API**: `FireProx`, `FireObject`, `FireCollection` - Wraps `firestore.Client`
* **Asynchronous API**: `AsyncFireProx`, `AsyncFireObject`, `AsyncFireCollection` - Wraps `firestore.AsyncClient`

**Base Class Architecture**: To maximize code reuse and maintain consistency between the synchronous and asynchronous implementations, FireProx employs a base class pattern:

* **BaseFireObject**: Contains all state management logic, property accessors (`id`, `path`, `state`), state inspection methods (`is_loaded()`, `is_dirty()`, etc.), and attribute handling helpers that are identical between sync and async versions.
* **BaseFireCollection**: Contains shared collection properties (`id`, `path`) and string representations.
* **BaseFireProx**: Contains shared path validation logic and client access properties.

The concrete `FireObject` and `AsyncFireObject` classes inherit from `BaseFireObject` and implement only the I/O operations (`fetch()`, `save()`, `delete()`) that differ between synchronous and asynchronous execution.

**Key Differences**:

1. **Lazy Loading**:
   - **Synchronous** (`FireObject`): ATTACHED objects automatically fetch data on first attribute access via `__getattr__`. This provides seamless lazy loading.
   - **Asynchronous** (`AsyncFireObject`): Python does not support async `__getattr__`, so ATTACHED objects require an explicit `await fetch()` call before accessing attributes. Attempting to access an attribute on an ATTACHED async object raises a clear error message: `"Cannot access attribute 'name' on ATTACHED AsyncFireObject. Call await fetch() first."`

2. **Method Signatures**:
   - Synchronous: `user.save()`, `user.fetch()`, `user.delete()`
   - Asynchronous: `await user.save()`, `await user.fetch()`, `await user.delete()`

**Development Principle**: When adding new features, **always implement for both sync and async versions**. Use the base classes for any logic that can be shared (state management, validation, properties) and implement only the I/O operations separately in the concrete classes.

**Example Usage**:

Python (Synchronous)
```python
from google.cloud import firestore
from fireprox import FireProx

client = firestore.Client(project='my-project-id')
db = FireProx(client)

user = db.doc('users/alovelace')
print(user.name)  # Lazy loads automatically
```

Python (Asynchronous)
```python
from google.cloud import firestore
from fireprox import AsyncFireProx

client = firestore.AsyncClient(project='my-project-id')
db = AsyncFireProx(client)

user = db.doc('users/alovelace')
await user.fetch()  # Explicit fetch required
print(user.name)
```

## **VI. Architectural Blueprint and Path Forward**

### **A. Component Interaction Diagram**

The architecture can be visualized as a layered system. At the bottom is the google-cloud-firestore library, handling the low-level communication with the Firestore service. The FireProx library sits on top of this, with the FireObject as its central abstraction. Developer code interacts exclusively with FireObject and its associated components (ProxiedMap, ProxiedList, and query builders). When an action like .save() or .fetch() is called on a FireObject, it translates the request into the appropriate calls on the underlying DocumentReference or Client objects from the native library.

* **Developer Code**: Interacts with `FireObject`/`AsyncFireObject`, `FireCollection`/`AsyncFireCollection`, `ProxiedMap`, `ProxiedList`.
* **FireProx Layer**:
  * **Base Classes**: `BaseFireObject` (state management, properties), `BaseFireCollection` (collection properties), `BaseFireProx` (path validation)
  * **Sync Implementation**: `FireObject`, `FireCollection`, `FireProx` (wraps `firestore.Client`)
  * **Async Implementation**: `AsyncFireObject`, `AsyncFireCollection`, `AsyncFireProx` (wraps `firestore.AsyncClient`)
  * **Shared Components**: `ProxiedMap`/`ProxiedList` (track nested mutations), `FireQuery`/`AsyncFireQuery` (build queries)
* **Native Library Layer**:
  * **Sync**: `google.cloud.firestore.Client`, `DocumentReference`, `CollectionReference`, `WriteBatch`
  * **Async**: `google.cloud.firestore.AsyncClient`, `AsyncDocumentReference`, `AsyncCollectionReference`, `AsyncWriteBatch`
* **Firestore Service**: The remote database.

### **B. Recommended Implementation Roadmap**

A phased implementation is recommended to manage complexity and deliver value incrementally. **Each phase must be implemented for both synchronous and asynchronous APIs**, leveraging base classes to share common logic.

* **Phase 1: The Core FireObject and State Machine.** The initial focus should be on building the base class architecture (`BaseFireObject`, `BaseFireCollection`, `BaseFireProx`) with state management (DETACHED, ATTACHED, LOADED, DELETED). Implement the dynamic attribute handlers (\_\_getattr\_\_, \_\_setattr\_\_) and the basic lifecycle methods: fetch(), delete(), and a simple save() that performs a full overwrite (.set()). At this stage, dirty tracking will be a simple boolean flag. **Deliver both `FireObject`/`FireProx` (sync) and `AsyncFireObject`/`AsyncFireProx` (async) implementations.** All features should have integration tests for both sync and async versions using a real Firestore emulator.
* **Phase 2: Advanced save() Logic and Subcollections.** Enhance the save() method in both sync and async versions to use the \_dirty\_fields set to perform efficient partial updates (.update()) instead of full overwrites. Implement the .collection() method on both FireObject variants to enable subcollection access. Build the lightweight, chainable query builder (both `FireQuery` and `AsyncFireQuery`) and the .from\_snapshot() hydration method. Add atomic operations (ArrayUnion, ArrayRemove, Increment) support. **Integration tests required for both sync and async implementations.**
* **Phase 3: Mutation Tracking Proxies.** This is the most intricate part of the implementation. Develop the ProxiedMap and ProxiedList classes, ensuring they correctly inherit from their respective ABCs and transparently proxy all methods. Implement the mechanism for these proxies to report mutations back to their parent FireObject. These proxies must work correctly with both synchronous and asynchronous FireObject instances. **Test with both sync and async workflows.**
* **Phase 4: Refinements and Documentation.** With the core functionality in place, this phase should focus on adding helper methods, improving error handling, optimizing performance, and, most importantly, writing comprehensive documentation with clear examples and API references for both synchronous and asynchronous usage patterns.

### **C. Conclusion: Empowering the Prototyper**

The proposed architecture for the FireProx library directly addresses the need for a simplified, more intuitive interface for interacting with Google Cloud Firestore during the rapid prototyping phase of development. By introducing a schemaless, state-aware proxy object, it bridges the gap between Python's object-oriented paradigm and Firestore's document-based structure. The dynamic attribute handling, transparent mutation tracking, and clean API for subcollections and queries are all designed to remove friction and reduce boilerplate, allowing developers to focus on building and iterating on their application logic.

By intelligently wrapping—not replacing—the official google-cloud-firestore library, FireProx leverages the power and reliability of the native client while providing a higher-level abstraction optimized for developer velocity. It is a tool designed to get out of the developer's way, making working with Firestore in Python a more productive and enjoyable experience.

#### **Works cited**

1. Python Client for Cloud Firestore API ... \- Google Cloud, accessed September 18, 2025, [https://cloud.google.com/python/docs/reference/firestore/latest](https://cloud.google.com/python/docs/reference/firestore/latest)  
2. SDKs and client libraries | Firestore \- Firebase, accessed September 18, 2025, [https://firebase.google.com/docs/firestore/client/libraries](https://firebase.google.com/docs/firestore/client/libraries)  
3. Introduction to Google Firebase: Firestore using Python \- Analytics Vidhya, accessed September 18, 2025, [https://www.analyticsvidhya.com/blog/2022/07/introduction-to-google-firebase-firestore-using-python/](https://www.analyticsvidhya.com/blog/2022/07/introduction-to-google-firebase-firestore-using-python/)  
4. Essentials for Working With Firestore in Python | Towards Data Science, accessed September 18, 2025, [https://towardsdatascience.com/essentials-for-working-with-firestore-in-python-372f859851f7/](https://towardsdatascience.com/essentials-for-working-with-firestore-in-python-372f859851f7/)  
5. Class Client (2.21.0) | Python client library \- Google Cloud, accessed September 18, 2025, [https://cloud.google.com/python/docs/reference/firestore/latest/google.cloud.firestore\_v1.client.Client](https://cloud.google.com/python/docs/reference/firestore/latest/google.cloud.firestore_v1.client.Client)  
6. firestore-pydantic-odm · PyPI, accessed September 18, 2025, [https://pypi.org/project/firestore-pydantic-odm/](https://pypi.org/project/firestore-pydantic-odm/)  
7. billyrrr/firestore-odm: Object Document Mapper for Firestore. \- GitHub, accessed September 18, 2025, [https://github.com/billyrrr/firestore-odm](https://github.com/billyrrr/firestore-odm)  
8. firestore \- PyPI, accessed September 18, 2025, [https://pypi.org/project/firestore/](https://pypi.org/project/firestore/)  
9. Changelog \- Python client library | Google Cloud, accessed September 18, 2025, [https://cloud.google.com/python/docs/reference/firestore/latest/changelog](https://cloud.google.com/python/docs/reference/firestore/latest/changelog)  
10. Add and update data | Firestore \- Google Cloud, accessed September 18, 2025, [https://cloud.google.com/firestore/docs/manage-data/add-data](https://cloud.google.com/firestore/docs/manage-data/add-data)  
11. Best practices for Cloud Firestore \- Firebase, accessed September 18, 2025, [https://firebase.google.com/docs/firestore/best-practices](https://firebase.google.com/docs/firestore/best-practices)  
12. Using Firestore References to Avoid Redundancy: A Complete Guide | by Yash Rank, accessed September 18, 2025, [https://medium.com/@yashsojitra0/using-firestore-references-to-avoid-redundancy-a-complete-guide-ce6ce3f24423](https://medium.com/@yashsojitra0/using-firestore-references-to-avoid-redundancy-a-complete-guide-ce6ce3f24423)  
13. Firestore: save document reference or document id? \[closed\] \- Stack Overflow, accessed September 18, 2025, [https://stackoverflow.com/questions/73268217/firestore-save-document-reference-or-document-id](https://stackoverflow.com/questions/73268217/firestore-save-document-reference-or-document-id)  
14. Resolve Firestore References \- firebase \- Stack Overflow, accessed September 18, 2025, [https://stackoverflow.com/questions/48448352/resolve-firestore-references](https://stackoverflow.com/questions/48448352/resolve-firestore-references)  
15. Is there a way to resolve document references in a document when querying that document? : r/Firebase \- Reddit, accessed September 18, 2025, [https://www.reddit.com/r/Firebase/comments/f59znd/is\_there\_a\_way\_to\_resolve\_document\_references\_in/](https://www.reddit.com/r/Firebase/comments/f59znd/is_there_a_way_to_resolve_document_references_in/)