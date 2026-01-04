@router.post("/{plan_id}/clone", response_model=schemas.MealPlan)
def clone_plan(plan_id: int, request: dict, db: Session = Depends(get_db)):
    """Clone a plan to the current user's account."""
    # Request body: {"user_id": 123}
    user_id = request.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID required")
        
    original = db.query(orm.MealPlan).filter(orm.MealPlan.id == plan_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    # Create copy
    new_plan = orm.MealPlan(
        name=f"Copy of {original.name}",
        recipe_count=original.recipe_count,
        meal_types=original.meal_types,
        user_id=user_id,
        is_public=False, # Clones start private
        created_at=datetime.now()
    )
    
    # Optional: Clone pre-generated lists if suitable? 
    # Usually better to re-generate or start fresh. Let's start fresh.
    
    db.add(new_plan)
    db.flush()
    
    # Copy recipes
    for link in original.plan_recipes:
        new_link = orm.MealPlanRecipe(
            plan_id=new_plan.id,
            recipe_id=link.recipe_id,
            position=link.position
        )
        db.add(new_link)
        
    db.commit()
    db.refresh(new_plan)
    return new_plan
