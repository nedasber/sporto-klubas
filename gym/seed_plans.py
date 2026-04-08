from gym.models import MembershipPlan


def create_test_plans():
    print("=== PLANS SEED START ===")

    plans_data = [
        {
            "name": "1 mėn. neribotas",
            "duration_days": 30,
            "visit_limit": None,
            "price": 39.99,
        },
        {
            "name": "3 mėn. neribotas",
            "duration_days": 90,
            "visit_limit": None,
            "price": 99.99,
        },
        {
            "name": "10 apsilankymų",
            "duration_days": 60,
            "visit_limit": 10,
            "price": 49.99,
        },
        {
            "name": "Vienkartinis apsilankymas",
            "duration_days": 1,
            "visit_limit": 1,
            "price": 7.99,
        },
    ]

    for plan_data in plans_data:
        plan, created = MembershipPlan.objects.get_or_create(
            name=plan_data["name"]
        )

        plan.duration_days = plan_data["duration_days"]
        plan.visit_limit = plan_data["visit_limit"]
        plan.price = plan_data["price"]
        plan.save()

        print(
            f"Plan={plan.name}, created={created}, "
            f"duration={plan.duration_days}, visits={plan.visit_limit}, price={plan.price}"
        )

    print("All plans:", list(MembershipPlan.objects.values_list("name", flat=True)))
    print("=== PLANS SEED END ===")