from .knowledge import initialize_knowledge_graph
from .generalrag import GeneralRAG
from hyperon import MeTTa
from .utils import add_menu_item, get_menu_for_merchant, remove_menu_item

def assert_equal(actual, expected, msg=""):
	if actual != expected:
		raise AssertionError(f"{msg}\nExpected: {expected}\nActual:   {actual}")

def run_tests():
	print("[MeTTa] Initializing knowledge graph...")
	metta = MeTTa()
	initialize_knowledge_graph(metta)
	rag = GeneralRAG(metta)

	# RAG sanity checks
	print("[RAG] Checking specific models for ASI:One...")
	models = rag.get_specific_models("ASI:One")
	print("Models:", models)

	print("[RAG] Checking capabilities across specific models...")
	caps = rag.query_all_specific_capabilities("ASI:One")
	print("Capabilities:", caps)

	# Merchant menu tests
	merchant = "TestPizzaAgent"
	print("[Menu] Adding items...")
	add_menu_item(metta, merchant, "margherita", "9")
	add_menu_item(metta, merchant, "pepperoni", "11")
	# Debug: inspect raw menu pairs in the space
	raw_pairs = metta.run("!(match &self (menu $m $i) ($m $i))")
	print("Raw menu pairs:", raw_pairs)
	menu = get_menu_for_merchant(metta, merchant)
	print("Menu after add:", menu)
	# Order of results may vary based on store/query; assert set equality
	expected = set([("margherita", "9"), ("pepperoni", "11")])
	assert_equal(set(menu), expected, "Menu items mismatch after add")

	print("[Menu] Removing one item (pepperoni)...")
	remove_menu_item(metta, merchant, "pepperoni")
	menu_after_remove = get_menu_for_merchant(metta, merchant)
	print("Menu after remove:", menu_after_remove)
	expected_after = set([("margherita", "9")])
	assert_equal(set(menu_after_remove), expected_after, "Menu items mismatch after remove")

	print("All MeTTa tests passed ✔️")

if __name__ == "__main__":
	run_tests()