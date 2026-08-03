# evaluation/test_cases.py
# Source: Book 1, Chapter 9 (Appendix A — Code Wiring)
# 20-query labeled dataset covering five query categories:
# product identity, variants, care, policy, and out-of-scope.
# Written before running the evaluation — not after seeing scores. (Ch. 9)
# The out-of-scope case (winter wedding) encodes the expectation that
# the retriever withholds rather than answers.

TEST_CASES = [
    # ── Product identity and occasion ────────────────────────────────────────
    {
        "query": "Is the linen co-ord set suitable for summer?",
        "expected_answer": "Yes, the linen co-ord set is designed for summer casual wear.",
        "relevant_chunk_ids": ["p004_identity"],
    },
    {
        "query": "Can I wear the anarkali suit to a wedding?",
        "expected_answer": "Yes, the anarkali suit is festive wear suitable for weddings.",
        "relevant_chunk_ids": ["p005_identity"],
    },
    {
        "query": "Is the silk saree suitable for Diwali?",
        "expected_answer": "Yes, the silk saree is festive wear ideal for Diwali.",
        "relevant_chunk_ids": ["p003_identity"],
    },
    {
        "query": "Is there anything suitable for a festive occasion?",
        "expected_answer": "Yes, the silk saree and the anarkali suit are both festive wear.",
        "relevant_chunk_ids": ["p003_identity", "p005_identity"],
    },
    {
        "query": "Is there anything for casual daily wear?",
        "expected_answer": "Yes, the cotton kurta and the linen co-ord set are suited for casual daily wear.",
        "relevant_chunk_ids": ["p001_identity", "p004_identity"],
    },
    {
        "query": "What's good for a function?",
        "expected_answer": "The silk saree and the anarkali suit are both suitable for a function — both are festive wear designed for celebrations and formal occasions.",
        "relevant_chunk_ids": ["p003_identity", "p005_identity"],
    },
    # ── Variants: colour, size, price, stock ─────────────────────────────────
    {
        "query": "What colours does the silk saree come in?",
        "expected_answer": "The silk saree is available in red, gold, and emerald.",
        "relevant_chunk_ids": ["p003_variants"],
    },
    {
        "query": "What sizes does the anarkali suit come in?",
        "expected_answer": "The anarkali suit is available in sizes S to XXL.",
        "relevant_chunk_ids": ["p005_variants"],
    },
    {
        "query": "Do you have anything in teal?",
        "expected_answer": "Yes, the anarkali suit is available in teal.",
        "relevant_chunk_ids": ["p005_variants"],
    },
    {
        "query": "Can I get the woolen shawl in black?",
        "expected_answer": "The woolen shawl is available in charcoal grey and maroon, not black.",
        "relevant_chunk_ids": ["p002_variants"],
    },
    {
        "query": "Does the linen co-ord set come in beige?",
        "expected_answer": "Yes, the linen co-ord set is available in beige.",
        "relevant_chunk_ids": ["p004_variants"],
    },
    # ── Care instructions ─────────────────────────────────────────────────────
    {
        "query": "Does the cotton kurta need dry cleaning?",
        "expected_answer": "No, the cotton kurta is machine washable.",
        "relevant_chunk_ids": ["p001_care", "p001_identity"],
    },
    {
        "query": "How do I care for the woolen shawl?",
        "expected_answer": "The woolen shawl requires dry cleaning only.",
        "relevant_chunk_ids": ["p002_care"],
    },
    # ── Return and exchange policy ────────────────────────────────────────────
    {
        "query": "What is the return policy for the silk saree?",
        "expected_answer": "The silk saree can be returned within 7 days. It must be unstitched and unused.",
        "relevant_chunk_ids": ["p003_policy"],
    },
    # ── FAQs ─────────────────────────────────────────────────────────────────
    {
        "query": "Does the cotton kurta shrink after washing?",
        "expected_answer": "Minimal shrinkage of 2–3% may occur after the first wash.",
        "relevant_chunk_ids": ["p001_faq_0", "p001_care"],
    },
    {
        "query": "Does the silk saree come with a blouse?",
        "expected_answer": "No blouse is included. Blouse fabric can be sourced separately.",
        "relevant_chunk_ids": ["p003_faq_1"],
    },
    {
        "query": "Does the embroidered anarkali suit come with a dupatta?",
        "expected_answer": "Yes, the anarkali suit comes with a matching embroidered dupatta in teal.",
        "relevant_chunk_ids": ["p005_faq_0"],
    },
    {
        "query": "Does the Anarkali suit have a cotton lining?",
        "expected_answer": "I don't have information about the lining material for the Anarkali suit. For specific fabric details, please contact our team at support@zudyog.com.",
        "relevant_chunk_ids": [],
    },
    # ── Out-of-scope — system should withhold, not guess ─────────────────────
    {
        "query": "Do you have anything for a winter wedding?",
        "expected_answer": "I don't have a product that matches that specifically.",
        "relevant_chunk_ids": [],
    },
    {
        "query": "Do you sell men's sherwanis?",
        "expected_answer": "I don't have that specific information. Please reach our support team at support@zudyog.com for help.",
        "relevant_chunk_ids": [],
    },
]
