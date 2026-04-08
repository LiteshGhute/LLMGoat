# LLM08: Vector and Embedding Weakness

## Overview

This challenge demonstrates how an adversarially crafted document injected into a RAG vector store can **hijack chatbot responses for targeted queries** — purely by exploiting cosine similarity. You can see the attack happen live: inject a document through the UI and watch the chatbot's answers change in real time.

**Scenario:** CourseBot is NovaTech University's student assistant. Its vector store starts with only the legitimate course catalog. The injection panel on the right lets you add any document to the live vector store. The adversarial document is pre-loaded in the panel — it was crafted to rank #1 for enrollment-related queries by packing enrollment vocabulary densely, causing CourseBot to serve students a phishing URL and a false registration deadline.

---

## Solution:

**Step 1:** Launch **LLM08** and click **"Start Challenge"**.

![](./manual-assets/vector-embedding-weakness/0.jpg)

![](./manual-assets/vector-embedding-weakness/1.jpg)

The split-panel UI opens: chat on the left, the live vector store viewer and injection panel on the right. The store currently shows only **BASE** documents from the legitimate course catalog.

**Step 2:** Ask about enrollment before injecting — confirm the chatbot gives correct information.

**Prompt:**
```
How do I enroll in courses for next semester?
```

![](./manual-assets/vector-embedding-weakness/2.jpg)

CourseBot correctly returns the official portal: `https://portal.novatech.edu/enroll`. The vector store is clean.

**Step 3:** Inject the adversarial document.

The injection panel is pre-filled with the crafted document. Click **"Inject into Store"**.

![](./manual-assets/vector-embedding-weakness/3.jpg)

The vector store panel immediately shows a new **INJECTED** entry highlighted in red. The document has been embedded and is now part of the retrieval pool.

**Step 4:** Ask the same enrollment question again.

**Prompt:**
```
How do I enroll in courses for next semester?
```

![](./manual-assets/vector-embedding-weakness/4.jpg)

CourseBot now returns the phishing URL: `https://novatech-student-portal.co/register` — the adversarial document outscored the real enrollment page in cosine similarity.

**Step 5:** Check the deadline.

**Prompt:**
```
What is the deadline to register for courses?
```

![](./manual-assets/vector-embedding-weakness/5.jpg)

CourseBot returns **November 1st** — the attacker's false deadline. The real deadline (January 10th) was outranked.

---

## Why the Injected Document Wins

The adversarial document was engineered to pack the highest density of enrollment-related terms: *enrollment, register, registration, sign up, courses, semester, tuition, payment, deadline, portal, student.* This is the exact vocabulary students use in enrollment queries.

Cosine similarity rewards shared vocabulary and semantic overlap. The legitimate enrollment section spreads these terms across multiple paragraphs. The adversarial document concentrates them all in one chunk — maximising its similarity score for every enrollment-related query.

The RAG pipeline has **no provenance check** — it cannot distinguish between a document from the official registrar and one injected by an attacker. Both are just vectors. The highest score wins.

---

## Remediation

- **Access control on the vector store.** Only verified sources should be allowed to add documents.
- **Document provenance metadata.** Tag every chunk with its source. Filter to trusted sources before retrieval.
- **Anomaly detection.** Flag queries where one document dominates the top scores — may indicate an adversarially optimised injection.
- **Human review of store additions.** No document should enter a production knowledge base through automated ingestion without review.

---

End of the Challenge!
