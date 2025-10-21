import json
from openai import OpenAI
from .generalrag import GeneralRAG
from hyperon import MeTTa, E, S, ValueAtom

def create_metta() -> MeTTa:
    """Factory to create and return a MeTTa instance."""
    return MeTTa()

def _has_any_match(res) -> bool:
    """Return True if the MeTTa result set contains any non-empty match.
    Hyperon can return structures like [[], []] when there are no matches.
    """
    if not res:
        return False
    for row in res:
        # A non-list row is a match
        if not isinstance(row, list):
            return True
        # A list row with any elements is a match
        if isinstance(row, list) and len(row) > 0:
            return True
    return False

def add_menu_item(metta: MeTTa, merchant_name: str, item_name: str, price: str):
    """Upsert a merchant menu item: ensure single (menu <merchant> <item>) and append (price <item> <value>).
    Uses Python-side existence check to be robust to merchant names with special chars (e.g., addresses).
    """
    existing = {i for (i, _p) in (get_menu_for_merchant(metta, merchant_name) or [])}
    if item_name in existing:
        # Only append a new price value
        metta.space().add_atom(E(S("price"), S(item_name), ValueAtom(price)))
        return
    # Otherwise create both relations
    metta.space().add_atom(E(S("menu"), S(merchant_name), S(item_name)))
    metta.space().add_atom(E(S("price"), S(item_name), ValueAtom(price)))

def get_menu_for_merchant(metta: MeTTa, merchant_name: str):
    """Retrieve items for a merchant: returns list of (item, price).

    Implementation note: We first collect all (merchant, item) pairs from the graph and
    filter in Python. This avoids edge cases with symbol quoting in MeTTa query strings.
    """
    pairs = metta.run("!(match &self (menu $m $i) ($m $i))")
    results = []
    seen_items = set()

    def handle_pair(m_sym: str, i_sym: str):
        if m_sym != merchant_name:
            return
        # Deduplicate by item symbol
        if i_sym in seen_items:
            return
        removed_res = metta.run(f"!(match &self (removed-menu {m_sym} {i_sym}) $x)")
        if _has_any_match(removed_res):
            return
        price_res = metta.run(f"!(match &self (price {i_sym} $p) $p)")
        # Use the latest price if multiple price entries exist
        price = _latest_value_from_match(price_res)
        results.append((i_sym, price))
        seen_items.add(i_sym)

    for r in pairs or []:
        # Case 1: r looks like [m, i]
        if isinstance(r, list) and len(r) == 2 and not str(r[0]).startswith("("):
            handle_pair(str(r[0]), str(r[1]))
            continue
        # Case 2: r is a list of expression atoms like "(m i)"
        if isinstance(r, list):
            for e in r:
                s = str(e)
                if s.startswith("(") and s.endswith(")"):
                    try:
                        m_sym, i_sym = s[1:-1].split(" ", 1)
                        handle_pair(m_sym, i_sym)
                    except ValueError:
                        continue
        else:
            # Fallback: try to parse a single expression atom
            s = str(r)
            if s.startswith("(") and s.endswith(")"):
                try:
                    m_sym, i_sym = s[1:-1].split(" ", 1)
                    handle_pair(m_sym, i_sym)
                except ValueError:
                    pass
    return results

# Merchant metadata helpers

def set_merchant_description(metta: MeTTa, merchant_name: str, description: str):
    """Set or update a merchant's public description."""
    metta.space().add_atom(E(S("merchant-desc"), S(merchant_name), ValueAtom(description)))

def get_merchant_description(metta: MeTTa, merchant_name: str):
    """Get the latest merchant description, if any."""
    res = metta.run(f"!(match &self (merchant-desc {merchant_name} $d) $d)")
    return res[-1][0].get_object().value if res and res[-1] else None

def set_open_hours(metta: MeTTa, merchant_name: str, hours: str):
    """Set store open hours, e.g., 'Mon-Sun 10:00-22:00'."""
    metta.space().add_atom(E(S("merchant-hours"), S(merchant_name), ValueAtom(hours)))

def get_open_hours(metta: MeTTa, merchant_name: str):
    res = metta.run(f"!(match &self (merchant-hours {merchant_name} $h) $h)")
    return res[-1][0].get_object().value if res and res[-1] else None

def set_location(metta: MeTTa, merchant_name: str, location: str):
    metta.space().add_atom(E(S("merchant-location"), S(merchant_name), ValueAtom(location)))

def get_location(metta: MeTTa, merchant_name: str):
    res = metta.run(f"!(match &self (merchant-location {merchant_name} $l) $l)")
    return res[-1][0].get_object().value if res and res[-1] else None

def add_category(metta: MeTTa, merchant_name: str, category: str):
    metta.space().add_atom(E(S("merchant-category"), S(merchant_name), S(category)))

def list_categories(metta: MeTTa, merchant_name: str):
    res = metta.run(f"!(match &self (merchant-category {merchant_name} $c) $c)")
    return [str(r[0]) for r in (res or []) if r]

# Merchant wallet

def set_merchant_wallet(metta: MeTTa, merchant_name: str, wallet_address: str):
    """Store or update merchant payout wallet address."""
    metta.space().add_atom(E(S("merchant-wallet"), S(merchant_name), ValueAtom(wallet_address)))

def get_merchant_wallet(metta: MeTTa, merchant_name: str):
    res = metta.run(f"!(match &self (merchant-wallet {merchant_name} $w) $w)")
    return res[-1][0].get_object().value if res and res[-1] else None

# Item details

def set_item_description(metta: MeTTa, item_name: str, description: str):
    metta.space().add_atom(E(S("item-desc"), S(item_name), ValueAtom(description)))

def get_item_description(metta: MeTTa, item_name: str):
    res = metta.run(f"!(match &self (item-desc {item_name} $d) $d)")
    return res[-1][0].get_object().value if res and res[-1] else None

def update_item_price(metta: MeTTa, item_name: str, new_price: str):
    """Append a new price value; retrieval will use the latest entry."""
    metta.space().add_atom(E(S("price"), S(item_name), ValueAtom(new_price)))

def get_item_price(metta: MeTTa, item_name: str):
    res = metta.run(f"!(match &self (price {item_name} $p) $p)")
    # Prefer the latest entry regardless of row/value shape
    return _latest_value_from_match(res)

def _latest_value_from_match(res):
    """Extract the latest scalar value from a MeTTa run() match result.
    Handles shapes like: [["10", "14"]] or [[ValueAtom(10)], [ValueAtom(14)]] or [[10]]
    Returns a string value when possible.
    """
    if not res:
        return None
    row = res[-1]
    # If the row is a list with multiple values, take the last value
    if isinstance(row, list) and row:
        val = row[-1]
    else:
        val = row
    # Unwrap possible nested single-element lists
    if isinstance(val, list) and val:
        val = val[-1]
    # Try to access atom object value if present
    try:
        return val.get_object().value  # type: ignore[attr-defined]
    except Exception:
        return str(val)

def remove_menu_item(metta: MeTTa, merchant_name: str, item_name: str):
    """Soft-remove a menu item by writing a tombstone relation (removed-menu merchant item)."""
    metta.space().add_atom(E(S("removed-menu"), S(merchant_name), S(item_name)))
    return True

class LLM:
    def __init__(self, api_key):
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.asi1.ai/v1"
        )

    def create_completion(self, prompt, max_tokens=200):
        completion = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="asi1-mini",  # ASI:One model name
            max_tokens=max_tokens
        )
        return completion.choices[0].message.content

def get_intent_and_keyword(query, llm):
    """Use ASI:One API to classify intent and extract a keyword."""
    prompt = (
        f"Given the query: '{query}'\n"
        "Classify the intent as one of: 'capability', 'solution', 'consideration', 'faq', or 'unknown'.\n"
        "Extract the most relevant keyword (e.g., a concept, problem, or topic) from the query.\n"
        "Return *only* the result in JSON format like this, with no additional text:\n"
        "{\n"
        "  \"intent\": \"<classified_intent>\",\n"
        "  \"keyword\": \"<extracted_keyword>\"\n"
        "}"
    )
    response = llm.create_completion(prompt)
    try:
        result = json.loads(response)
        return result["intent"], result["keyword"]
    except json.JSONDecodeError:
        print(f"Error parsing ASI:One response: {response}")
        return "unknown", None

def generate_knowledge_response(query, intent, keyword, llm):
    """Use ASI:One to generate a response for new knowledge based on intent."""
    if intent == "capability":
        prompt = (
            f"Query: '{query}'\n"
            "The concept '{keyword}' is not in my knowledge base. Suggest plausible capabilities it might have.\n"
            "Return *only* the capability description, no additional text."
        )
    elif intent == "solution":
        prompt = (
            f"Query: '{query}'\n"
            "The problem '{keyword}' has no known solutions in my knowledge base. Suggest a plausible solution.\n"
            "Return *only* the solution description, no additional text."
        )
    elif intent == "consideration":
        prompt = (
            f"Query: '{query}'\n"
            "The topic '{keyword}' has no known considerations in my knowledge base. Suggest plausible considerations or limitations.\n"
            "Return *only* the considerations description, no additional text."
        )
    elif intent == "faq":
        prompt = (
            f"Query: '{query}'\n"
            "This is a new FAQ not in my knowledge base. Provide a concise, helpful answer about Fetch.ai/uAgents.\n"
            "Return *only* the answer, no additional text."
        )
    else:
        return None
    return llm.create_completion(prompt)

def process_query(query, rag: GeneralRAG, llm: LLM):
    intent, keyword = get_intent_and_keyword(query, llm)
    print(f"Intent: {intent}, Keyword: {keyword}")
    prompt = ""

    if intent == "faq":
        faq_answer = rag.query_faq(query)
        if not faq_answer and keyword:
            new_answer = generate_knowledge_response(query, intent, keyword, llm)
            rag.add_knowledge("faq", query, new_answer)
            print(f"Knowledge graph updated - Added FAQ: '{query}' → '{new_answer}'")
            prompt = (
                f"Query: '{query}'\n"
                f"FAQ Answer: '{new_answer}'\n"
                "Humanize this for a Fetch.ai/uAgents assistant with a helpful tone."
            )
        elif faq_answer:
            prompt = (
                f"Query: '{query}'\n"
                f"FAQ Answer: '{faq_answer}'\n"
                "Humanize this for a Fetch.ai/uAgents assistant with a helpful tone."
            )
    elif intent == "capability" and keyword:
        capabilities = rag.query_capability(keyword)
        if not capabilities:
            capability = generate_knowledge_response(query, intent, keyword, llm)
            rag.add_knowledge("capability", keyword, capability)
            print(f"Knowledge graph updated - Added capability: '{keyword}' → '{capability}'")
            solutions = rag.get_solution(keyword) or ["consult documentation"]
            considerations = [rag.get_consideration(keyword)] if keyword else []
            prompt = (
                f"Query: '{query}'\n"
                f"Concept: {keyword}\n"
                f"Capabilities: {capability}\n"
                f"Solutions: {', '.join(solutions)}\n"
                f"Considerations: {', '.join([', '.join(c) for c in considerations if c])}\n"
                "Generate a concise, helpful response for a Fetch.ai/uAgents assistant."
            )
        else:
            capability = capabilities[0]
            solutions = rag.get_solution(keyword)
            considerations = [rag.get_consideration(keyword)] if keyword else []
            prompt = (
                f"Query: '{query}'\n"
                f"Concept: {keyword}\n"
                f"Capabilities: {capability}\n"
                f"Solutions: {', '.join(solutions)}\n"
                f"Considerations: {', '.join([', '.join(c) for c in considerations if c])}\n"
                "Generate a concise, helpful response for a Fetch.ai/uAgents assistant."
            )
    elif intent == "solution" and keyword:
        solutions = rag.get_solution(keyword)
        if not solutions:
            solution = generate_knowledge_response(query, intent, keyword, llm)
            rag.add_knowledge("solution", keyword, solution)
            print(f"Knowledge graph updated - Added solution: '{keyword}' → '{solution}'")
            prompt = (
                f"Query: '{query}'\n"
                f"Problem: {keyword}\n"
                f"Solution: {solution}\n"
                "Provide a helpful solution suggestion."
            )
        else:
            prompt = (
                f"Query: '{query}'\n"
                f"Problem: {keyword}\n"
                f"Solutions: {', '.join(solutions)}\n"
                "Provide a helpful solution suggestion."
            )
    elif intent == "consideration" and keyword:
        considerations = rag.get_consideration(keyword)
        if not considerations:
            consideration = generate_knowledge_response(query, intent, keyword, llm)
            rag.add_knowledge("consideration", keyword, consideration)
            print(f"Knowledge graph updated - Added consideration: '{keyword}' → '{consideration}'")
            prompt = (
                f"Query: '{query}'\n"
                f"Topic: {keyword}\n"
                f"Considerations: {consideration}\n"
                "Provide a concise explanation of considerations."
            )
        else:
            prompt = (
                f"Query: '{query}'\n"
                f"Topic: {keyword}\n"
                f"Considerations: {', '.join(considerations)}\n"
                "Provide a concise explanation of considerations."
            )
    
    if not prompt:
        prompt = f"Query: '{query}'\nNo specific info found. Offer general Fetch.ai/uAgents assistance."

    prompt += "\nFormat response as: 'Selected Question: <question>' on first line, 'Humanized Answer: <response>' on second."
    response = llm.create_completion(prompt)
    try:
        selected_q = response.split('\n')[0].replace("Selected Question: ", "").strip()
        answer = response.split('\n')[1].replace("Humanized Answer: ", "").strip()
        return {"selected_question": selected_q, "humanized_answer": answer}
    except IndexError:
        return {"selected_question": query, "humanized_answer": response}