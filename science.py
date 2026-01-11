import random

LIVING = ["Dog", "Cat", "Tree", "Bird"]
NON_LIVING = ["Table", "Stone", "Chair", "Book"]

ENERGY = ["Heat", "Light", "Sound", "Electricity"]

def generate_science_question(grade):

    if grade <= 3:
        correct = random.choice(LIVING)
        options = random.sample(NON_LIVING, 3) + [correct]
        question = "Which of these is a living thing?"

    elif grade <= 6:
        correct = "Sun"
        options = ["Moon", "Bulb", "Sun", "Fire"]
        question = "What is the main source of energy for Earth?"

    else:
        correct = random.choice(ENERGY)
        options = random.sample(ENERGY, 3) + ["Gravity"]
        question = "Which of these is a form of energy?"

    random.shuffle(options)

    return {
        "q": question,
        "options": options,
        "answer": correct
    }
