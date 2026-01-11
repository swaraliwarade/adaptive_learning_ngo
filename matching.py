def find_matches(students):
    matches = []

    for mentor in students:
        for mentee in students:

            # Do not match a student with themselves
            if mentor["name"] == mentee["name"]:
                continue

            score = 0

            # Skill match: mentor strong where mentee is weak
            for skill in mentor["good_at"]:
                if skill in mentee["weak_at"]:
                    score += 2

            # Time slot match
            if mentor["time"] == mentee["time"]:
                score += 1

            if score > 0:
                matches.append({
                    "Mentor": mentor["name"],
                    "Mentee": mentee["name"],
                    "Score": score
                })

    # Sort by highest score first
    matches.sort(key=lambda x: x["Score"], reverse=True)

    return matches
