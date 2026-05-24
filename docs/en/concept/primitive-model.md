# The Primitive Model — Why This Layer Exists

## The Problem

Every managed infrastructure object — a Kubernetes Pod, a network interface, a database
instance — needs to be described somewhere: what fields it has, what operations can be
performed on it, how its desired state differs from its observed state.

Without a shared foundation, each domain invents its own schema language. The result:

- 50 domain repos, 50 incompatible schema formats for the same semantic concepts
- "config" means something different in every repo
- Validation logic is copy-pasted and diverges silently
- No machine-checkable contract between a schema and its downstream consumers

The primitive model exists to prevent this.

---

## What a Primitive Is

A primitive is an **irreducible semantic atom** — something that cannot be broken down
further without losing infrastructure management meaning.

There are exactly 7 atomic primitives:

| Atom | What it captures |
|---|---|
| **Shape** | Data structure — what fields, what types |
| **Role** | Management semantics — config? state? key? reference? |
| **Behavior** | What operations can be performed |
| **Contract** | What constraints must hold |
| **Address** | How the entity is reachable |
| **Identity** | What it is (type identity, not instance identity) |
| **Event** | What async signals it can emit |

These are not YANG concepts, not RESTCONF concepts — they are the semantic layer
*beneath* any specific schema language.

---

## Two Levels

```
atomic primitive   = irreducible semantic atom
                     → schema fragment generator

aggregate primitive = semantic composition with sealed/defaulted/required slots
                     → the actual design unit
```

You never start from an atomic. You start from an aggregate.

```
ManagedEntity =
  Identity + ConfigSurface + StateSurface +
  OperationSurface + NotificationSurface +
  CapabilitySurface + LifecycleSurface + BindingSurface
```

A domain object (KubernetesPod, NetworkInterface, DatabaseInstance) is a
**specialization** of ManagedEntity — never a new invention.

---

## The Slot Contract

Every aggregate defines its slots with an explicit mode:

| Mode | Meaning |
|---|---|
| `sealed` | Fixed in the aggregate — a domain specialization cannot override it |
| `defaulted` | Has a default — a domain specialization may override it |
| `required` | Must be defined in every domain specialization |

This is machine-checked by `compiler.py` on every `make validate` run.

---

## The Composition Mechanism

Inheritance is not YAML override rules. It is git:

```
base-repo
  └─[remote: base]─► cic-primitives
                          └─[remote: base]─► domain repos
```

A domain repo merges `cic-primitives@v0.1.0` as a git remote. The file structure
*is* the interface contract. A merge conflict *is* a schema violation.

---

## The Three Questions

Every primitive is only complete when all three are answerable:

1. **How does this become a YAML schema?** → `make validate` green
2. **How does this become an API?** → `derivation_chain.restconf` documented
3. **How does this become runtime behavior?** → `derivation_chain.runtime` documented

See `schemas/examples/kubernetes-pod.yaml` for a complete worked example.
