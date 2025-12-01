from agent import run_agent

def main():
    print("💰 Personal Finance Agent (type 'exit' to quit)\n")
    while True:
        question = input("You: ")
        if question.lower() in ["exit", "quit", "q"]:
            print("👋 Goodbye!")
            break

        try:
            answer = run_agent(question)
            print(f"AI: {answer}\n")
        except Exception as e:
            print(f"⚠️ Error: {e}\n")

if __name__ == "__main__":
    main()
