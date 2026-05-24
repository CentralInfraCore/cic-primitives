# CIC Validation and Schema-Based Model

## Core Concepts

In the CIC system, every component (module, relay, output) and its configuration is strictly governed by schema-based validation. The schema defines not only structure but also behavior and permissions.

This ensures the system is:

* declarative,
* self-validating,
* equipped with built-in self-protection mechanisms.

---

## 1. Role of the Schema

The schema defines every key of an object, its expected type, default values, and allowed values.

### Key properties:

* `required`: key must be present
* `default`: fallback value if key is missing
* `nullable`: whether null/None is acceptable
* `enum`: predefined list of accepted values

---

## 2. Validation Process

1. **Loading:** The YAML/JSON configuration object is loaded.
2. **Schema Assignment:** Based on version, the appropriate schema definition is attached.
3. **Validation:** Keys, types, and constraints are checked.
4. **Population:** Default values are automatically filled in.
5. **Feedback:** Valid/invalid result is returned with stored audit metadata.

---

## 3. Schema Inheritance

Schemas may inherit from one another, enabling:

* unified handling of module families,
* consistent versioning,
* description of complex interfaces with minimal duplication.

A relay only accepts a module if its schema:

* is successfully validated,
* refers to an active version,
* does not conflict with the current execution graph.

---

## 4. Validation as an Educational Tool

The validation system itself supports learning:

* all schemas are published and open,
* all validation errors return human-readable feedback,
* the building process is deterministic,
* thus, developers and AI alike can learn from errors.

---

## 5. Sample Schema File Structure

```yaml
version: v1
kind: relay.module
spec:
  name:
    type: string
    required: true
  inputs:
    type: array
    items:
      type: object
      properties:
        type:
          type: string
          required: true
  config:
    type: object
    properties:
      retries:
        type: integer
        default: 3
      timeout:
        type: number
        default: 5.0
      secure:
        type: boolean
        default: true
```

### 5.1 Behavior and Role of Default Values in Validation

The `default` field is not merely a convenience — it's a **guarantee of deterministic behavior**.

Using default values:

* **during mandatory validation**: if a non-required field is missing, the default is inserted automatically,
* **to preserve interface conformity**: the executing relay or module always receives a predictable configuration shape,
* **for self-healing operation**: in case of minor errors or missing keys, the system continues running with meaningful defaults.

This behavior is built into the validation pipeline and enforced uniformly across all contexts.

---

## 6. Conclusion

The schema-based model provides not only syntactic but also **structural guarantees** for system behavior.
Therefore, the CIC system is:

* validatable,
* reproducible,
* AI-controllable,
* auditable,
* educational.

This verifiable schema model is the foundation of why the system can be open, yet secure.