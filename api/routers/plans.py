
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import random
from datetime import datetime

from api.database import get_db
from api.models import orm
from api import schemas

router = APIRouter(
    prefix="/api/plans",
    tags=["plans"]
)

@router.post("/generate", response_model=schemas.MealPlan)
def generate_plan(request: schemas.PlanGenerateRequest, db: Session = Depends(get_db)):
    """
    Generate a new meal plan with stratified random recipes.
    Supports days-based count, catalog filtering, and exclusions.
    """
    selected_recipes = []
    
    # Determine strategy
    # If 'days' is provided, we want X recipes PER type (e.g. 5 days of Breakfast + Dinner = 10 recipes)
    count_per_type = 0
    if request.days and request.days > 0:
        count_per_type = request.days
    else:
        # Legacy/Total Count mode: Distribute total across types
        # e.g. 5 recipes, 2 types -> 2 and 3.
        # But we'll handle this dynamically if needed. For now, let's assume balanced.
        if request.meal_types:
            count_per_type = max(1, request.recipe_count // len(request.meal_types))
            # Note: This logic might under-count if there's a remainder, 
            # but user complaint was about balance.
    
    # Exclusions preparation
    exclusions = [e.lower().strip() for e in request.excluded_ingredients] if request.excluded_ingredients else []
    
    # If NO meal types selected, we act in "Any" mode
    if not request.meal_types:
        # Select purely random recipes matching catalog/exclusions
        query = db.query(orm.Recipe)
        if request.catalog_id:
            query = query.filter(orm.Recipe.catalog_id == request.catalog_id)
            
        candidates = query.all()
        
        # Apply Exclusions
        valid_candidates = []
        if exclusions:
            for r in candidates:
                is_excluded = False
                if any(ex in r.name.lower() for ex in exclusions): is_excluded = True
                else: 
                     for ing in r.ingredients:
                        if any(ex in ing.ingredient_text.lower() for ex in exclusions):
                            is_excluded = True; break
                if not is_excluded: valid_candidates.append(r)
        else:
            valid_candidates = candidates
            
        # Select target count
        # If days provided, assume 1 recipe per day? Or request.recipe_count?
        # Typically slider maps to request.recipe_count (days).
        # Let's use request.recipe_count as target total.
        target_count = request.recipe_count
        
        if len(valid_candidates) <= target_count:
            selected_recipes = valid_candidates
        else:
            selected_recipes = random.sample(valid_candidates, target_count)

    else:
        # Standard Stratified Logic
        for m_type in request.meal_types:

            query = db.query(orm.Recipe).filter(orm.Recipe.meal_type == m_type)
            
            if request.catalog_id:
                query = query.filter(orm.Recipe.catalog_id == request.catalog_id)
                
            candidates = query.all()
            
            # Filter exclusions (Python side for flexibility)
            valid_candidates = []
            if exclusions:
                for r in candidates:
                    # Check name and ingredients
                    is_excluded = False
                    
                    # Check name
                    if any(ex in r.name.lower() for ex in exclusions):
                        is_excluded = True
                    else:
                        # Check ingredients
                        for ing in r.ingredients:
                            if any(ex in ing.ingredient_text.lower() for ex in exclusions):
                                is_excluded = True
                                break
                                
                    if not is_excluded:
                        valid_candidates.append(r)
            else:
                valid_candidates = candidates
                
            # Select
            count_needed = count_per_type
            
            # Handling legacy manual count remainder if 'days' wasn't used?
            # If 'days' is not used, request.recipe_count applies globally.
            # This loop logic assumes stratified.
            # If user asked for 5 total, and we have 2 types, we calculated count_per_type = 2.
            # Total = 4. We miss 1.
            # Ideally we'd add the remainder to one type. 
            # But for the specific user request "5 and 5", they likely mean Days.
            
            if len(valid_candidates) <= count_needed:
                selected_recipes.extend(valid_candidates)
            else:
                selected_recipes.extend(random.sample(valid_candidates, count_needed))
            
    # Handle remainder for fixed total count if needed (only if days wasn't used)
    # If using 'days', strictly stick to stratified count (days * types) even if it means missing some if not enough recipes.
    
    # Generate creative name using AI
    from api.services import ai_service
    
    # Convert SQLAlchemy objects to dicts for AI
    recipe_dicts = []
    for r in selected_recipes:
        recipe_dicts.append({
            "name": r.name,
            "serves": r.serves,
            "ingredients": [{"ingredient_text": i.ingredient_text} for i in r.ingredients]
        })
        
    try:
        plan_name = ai_service.generate_plan_name(recipe_dicts)
    except Exception as e:
        print(f"AI Naming failed: {e}")
        plan_name = f"Plan {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
    # Create MealPlan object
    new_plan = orm.MealPlan(
        name=plan_name,
        recipe_count=len(selected_recipes),
        meal_types=request.meal_types,
        user_id=request.user_id,
        created_at=datetime.now()
    )
    db.add(new_plan)
    db.flush()
    
    # Create linkages
    for i, recipe in enumerate(selected_recipes):
        link = orm.MealPlanRecipe(
            plan_id=new_plan.id,
            recipe_id=recipe.id,
            position=i
        )
        db.add(link)
    
    db.commit()
    db.refresh(new_plan)
    return new_plan

@router.get("/", response_model=List[schemas.MealPlan])
def read_plans(
    skip: int = 0, 
    limit: int = 20, 
    user_id: Optional[int] = None, 
    scope: str = "my", # "my" or "community"
    db: Session = Depends(get_db)
):
    """List meal plans (My Plans or Community Plans)."""
    query = db.query(orm.MealPlan)
    
    if scope == "community":
        # Show public plans only
        query = query.filter(orm.MealPlan.is_public == True)
        # Optionally exclude own plans? Or show all?
        # Usually show all public.
    else:
        # Default: Show my plans
        if user_id:
            query = query.filter(orm.MealPlan.user_id == user_id)
            
    return query.order_by(orm.MealPlan.created_at.desc()).offset(skip).limit(limit).all()

@router.post("/{plan_id}/share", response_model=schemas.MealPlan)
def share_plan(plan_id: int, request: dict, db: Session = Depends(get_db)):
    """Toggle public visibility."""
    # Request body: {"user_id": 123, "is_public": true}
    plan = db.query(orm.MealPlan).filter(orm.MealPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    # Verify ownership
    req_user_id = request.get("user_id")
    if plan.user_id != req_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this plan")
        
    is_public = request.get("is_public", False)
    new_name = request.get("new_name") # Optional rename during share
    
    if is_public:
        # Check Uniqueness among PUBLIC plans
        target_name = new_name if new_name else plan.name
        
        existing = db.query(orm.MealPlan).filter(
            orm.MealPlan.is_public == True,
            orm.MealPlan.name == target_name,
            orm.MealPlan.id != plan_id # Exclude self
        ).first()
        
        if existing:
             # Suggest a variation
             suggestion = f"{target_name} ({random.randint(100, 999)})"
             raise HTTPException(
                 status_code=409, 
                 detail=f"Plan name '{target_name}' is already taken in the community. Try '{suggestion}'?"
             )
    
    if new_name:
        plan.name = new_name
        
    plan.is_public = is_public
    
    # Auto-generate lists if missing and sharing
    if is_public:
        from api.services import ai_service
        
        # Check if lists exist
        needs_grocery = not (plan.grocery_list and plan.grocery_list.get("content"))
        needs_prep = not (plan.prep_plan and plan.prep_plan.get("content"))
        
        if needs_grocery or needs_prep:
            # Prepare recipes
            recipes = [link.recipe for link in plan.plan_recipes]
            recipe_dicts = []
            for r in recipes:
                r_dict = {
                    "name": r.name,
                    "serves": r.serves,
                    "ingredients": [{"ingredient_text": i.ingredient_text} for i in r.ingredients]
                }
                recipe_dicts.append(r_dict)
                
            if needs_grocery:
                try:
                    result_text = ai_service.generate_grocery_list(recipe_dicts)
                    plan.grocery_list = {"content": result_text}
                except Exception as e:
                    print(f"Auto-generate Grocery failed: {e}")
                    
            if needs_prep:
                try:
                    prep_text = ai_service.generate_prep_plan(recipe_dicts)
                    plan.prep_plan = {"content": prep_text}
                except Exception as e:
                    print(f"Auto-generate Prep failed: {e}")
    
    db.commit()
    db.refresh(plan)
    return plan

@router.post("/{plan_id}/like", response_model=schemas.MealPlan)
def like_plan(plan_id: int, request: dict, db: Session = Depends(get_db)):
    """Toggle like for a user."""
    # Request body: {"user_id": 123}
    user_id = request.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID required")
        
    plan = db.query(orm.MealPlan).filter(orm.MealPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Check existing like
    existing_like = db.query(orm.PlanLike).filter(
        orm.PlanLike.plan_id == plan_id,
        orm.PlanLike.user_id == user_id
    ).first()
    
    if existing_like:
        # Unlike
        db.delete(existing_like)
    else:
        # Like
        new_like = orm.PlanLike(user_id=user_id, plan_id=plan_id)
        db.add(new_like)
        
    db.commit()
    db.refresh(plan)
    return plan

@router.get("/{plan_id}", response_model=schemas.MealPlan)
def read_plan(plan_id: int, db: Session = Depends(get_db)):
    """Get a specific meal plan."""
    plan = db.query(orm.MealPlan).filter(orm.MealPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan

@router.delete("/{plan_id}")
def delete_plan(plan_id: int, db: Session = Depends(get_db)):
    """Delete a meal plan."""
    plan = db.query(orm.MealPlan).filter(orm.MealPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Identify recipes to check for GC (orphans)
    recipes_to_check = []
    for link in plan.plan_recipes:
        if link.recipe.catalog_id is None:
            recipes_to_check.append(link.recipe_id)
            
    db.delete(plan)
    db.flush() # Flush to update link counts
    
    # GC Logic
    for rid in recipes_to_check:
        usage = db.query(orm.MealPlanRecipe).filter(orm.MealPlanRecipe.recipe_id == rid).count()
        if usage == 0:
            db.query(orm.Recipe).filter(orm.Recipe.id == rid).delete()
            
    db.commit()
    return {"status": "success", "message": "Plan deleted"}

@router.patch("/{plan_id}", response_model=schemas.MealPlan)
def update_plan(plan_id: int, request: schemas.PlanUpdateRequest, db: Session = Depends(get_db)):
    """Update plan details (e.g. rename)."""
    plan = db.query(orm.MealPlan).filter(orm.MealPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    if request.user_id:
        if plan.user_id != request.user_id:
             raise HTTPException(status_code=403, detail="Not authorized to modify this plan")
    
    if request.name:
        plan.name = request.name
        
    db.commit()
    db.refresh(plan)
    return plan

@router.post("/{plan_id}/grocery", response_model=schemas.MealPlan)
def generate_grocery_list(plan_id: int, request: dict = None, db: Session = Depends(get_db)): # request might be empty dict or null
    """Generate grocery list for plan."""
    from api.services import ai_service
    
    plan = db.query(orm.MealPlan).filter(orm.MealPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    # Security: Check ownership if user_id provided
    if request and request.get("user_id"):
        if plan.user_id != request.get("user_id"):
             raise HTTPException(status_code=403, detail="Not authorized to modify this plan")

    # Return existing if present (unless forced - add param later if needed)
    if plan.grocery_list and plan.grocery_list.get("content"):
        return plan
        
    # Get full recipe objects
    # Access via relationship directly
    recipes = [link.recipe for link in plan.plan_recipes]
    
    # Convert SQLAlchemy objects to dicts for the service
    # The service expects dicts or objects with attributes. 
    # It handles both, but let's pass objects to be safe with our new logic.
    recipe_dicts = []
    for r in recipes:
        # Crude to_dict
        r_dict = {
            "name": r.name,
            "serves": r.serves,
            "ingredients": [{"ingredient_text": i.ingredient_text} for i in r.ingredients]
        }
        recipe_dicts.append(r_dict)
        
    result_text = ai_service.generate_grocery_list(recipe_dicts)
    
    # Update plan
    # We store it as a simple dict wrapper to match JSON column type
    plan.grocery_list = {"content": result_text}
    db.commit()
    db.refresh(plan)
    
    return plan

@router.post("/{plan_id}/prep", response_model=schemas.MealPlan)
def generate_prep_plan(plan_id: int, request: dict = None, db: Session = Depends(get_db)):
    """Generate prep plan for plan."""
    from api.services import ai_service
    
    plan = db.query(orm.MealPlan).filter(orm.MealPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    if request and request.get("user_id"):
        if plan.user_id != request.get("user_id"):
             raise HTTPException(status_code=403, detail="Not authorized to modify this plan")
        
    recipes = [link.recipe for link in plan.plan_recipes]
    recipe_dicts = []
    for r in recipes:
        r_dict = {
            "name": r.name,
            "serves": r.serves,
            "ingredients": [{"ingredient_text": i.ingredient_text} for i in r.ingredients]
        }
        recipe_dicts.append(r_dict)
        
    result_text = ai_service.generate_prep_plan(recipe_dicts)
    
    plan.prep_plan = {"content": result_text}
    db.commit()
    db.refresh(plan)
    
    return plan

@router.post("/{plan_id}/swap", response_model=schemas.MealPlan)
def swap_recipes(plan_id: int, request: schemas.SwapRequest, db: Session = Depends(get_db)):
    """
    Swap one or more recipes in a plan.
    Mode: "random" or "similar" (uses AI).
    """
    from api.services import ai_service

    plan = db.query(orm.MealPlan).filter(orm.MealPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    if request.user_id:
        if plan.user_id != request.user_id:
             raise HTTPException(status_code=403, detail="Not authorized to modify this plan")

    # Get current recipes in plan to exclude them from candidates
    # We maintain a set of current IDs to handle multiple swaps preventing duplicates
    current_recipe_ids = {link.recipe_id for link in plan.plan_recipes}

    for target_id in request.recipe_ids:
        # Find the specific link in the plan
        # We need the link object to update it
        target_link = next((link for link in plan.plan_recipes if link.recipe_id == target_id), None)
        
        if not target_link:
            continue # Skip if not found
            
        target_recipe = target_link.recipe
        
        # Find candidates: Not in current plan
        query = db.query(orm.Recipe).filter(orm.Recipe.id.notin_(current_recipe_ids))

        # Enforce Meal Type Strictness ONLY if:
        # 1. Plan has specific meal types defined
        # 2. AND we are NOT in 'catalog' mode (catalog mode implies "I want anything from this book")
        plan_has_types = bool(plan.meal_types)
        is_catalog_mode = (request.mode == "catalog")
        
        if plan_has_types and not is_catalog_mode:
             query = query.filter(orm.Recipe.meal_type == target_recipe.meal_type)
        
        # Apply catalog filter if mode is 'catalog'
        
        # Apply catalog filter if mode is 'catalog'
        if request.mode == "catalog" and request.catalog_id:
             query = query.filter(orm.Recipe.catalog_id == request.catalog_id)
        
        candidates = query.all()
        
        if not candidates:
            continue # No substitutes available
            
        new_recipe = None
        
        if request.mode == "random" or request.mode == "catalog":
            new_recipe = random.choice(candidates)
        elif request.mode == "similar":
            # Use AI to find best match
            # Convert candidates to dicts
            candidate_dicts = []
            for c in candidates:
                candidate_dicts.append({
                    "id": c.id,
                    "name": c.name,
                    "description": c.description,
                    "ingredients": [{"ingredient_text": i.ingredient_text} for i in c.ingredients]
                })
            
            target_dict = {
                "name": target_recipe.name,
                "description": target_recipe.description,
                "ingredients": [{"ingredient_text": i.ingredient_text} for i in target_recipe.ingredients]
            }
            
            best_id = ai_service.find_substitute(target_dict, candidate_dicts)
            
            if best_id:
                new_recipe = db.query(orm.Recipe).filter(orm.Recipe.id == best_id).first()
            
            # Fallback to random if AI fails or returns nothing
            if not new_recipe:
                 new_recipe = random.choice(candidates)
                 
        if new_recipe:
            # Execute Swap
            target_link.recipe_id = new_recipe.id
            
            # Update exclusion set
            current_recipe_ids.remove(target_id)
            current_recipe_ids.add(new_recipe.id)

    # Invalidate generated lists
    plan.grocery_list = None
    plan.prep_plan = None
    
    db.commit()
    db.refresh(plan)
    return plan

@router.post("/{plan_id}/remove", response_model=schemas.MealPlan)
def remove_recipes(plan_id: int, request: schemas.RecipeListRequest, db: Session = Depends(get_db)):
    """Remove specific recipes from a plan."""
    plan = db.query(orm.MealPlan).filter(orm.MealPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if request.user_id:
        if plan.user_id != request.user_id:
             raise HTTPException(status_code=403, detail="Not authorized to modify this plan")
        
    # GC prep
    recipes_to_check = []

    for rid in request.recipe_ids:
        # Check if orphan before removing link
        recipe = db.query(orm.Recipe).filter(orm.Recipe.id == rid).first()
        if recipe and recipe.catalog_id is None:
             recipes_to_check.append(rid)

        # Find and remove
        db.query(orm.MealPlanRecipe).filter(
            orm.MealPlanRecipe.plan_id == plan_id,
            orm.MealPlanRecipe.recipe_id == rid
        ).delete()
    
    db.flush()
    
    # GC Execute
    for rid in recipes_to_check:
         usage = db.query(orm.MealPlanRecipe).filter(orm.MealPlanRecipe.recipe_id == rid).count()
         if usage == 0:
              db.query(orm.Recipe).filter(orm.Recipe.id == rid).delete()
    
    # Update recipe counts and invalidate lists
    remaining_count = db.query(orm.MealPlanRecipe).filter(orm.MealPlanRecipe.plan_id == plan_id).count()
    plan.recipe_count = remaining_count
    plan.grocery_list = None
    plan.prep_plan = None
    
    db.commit()
    db.refresh(plan)
    return plan

@router.post("/{plan_id}/add", response_model=schemas.MealPlan)
def add_recipe(plan_id: int, request: schemas.RecipeAddRequest, db: Session = Depends(get_db)):
    """
    Add a recipe to the plan.
    Supports explicit ID or random selection.
    """
    plan = db.query(orm.MealPlan).filter(orm.MealPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    if request.user_id:
        if plan.user_id != request.user_id:
             raise HTTPException(status_code=403, detail="Not authorized to modify this plan")

    recipe_to_add = None
    
    current_ids = {link.recipe_id for link in plan.plan_recipes}
    
    if request.recipe_id:
        # Explicit Add
        if request.recipe_id in current_ids:
            return plan # Already in plan, do nothing or error? For UI simplicity, just return
            
        recipe_to_add = db.query(orm.Recipe).filter(orm.Recipe.id == request.recipe_id).first()
        
    elif request.random:
        # Random Add
        query = db.query(orm.Recipe).filter(orm.Recipe.id.notin_(current_ids))
        
        if request.catalog_id:
            query = query.filter(orm.Recipe.catalog_id == request.catalog_id)
            
        if request.meal_type:
            query = query.filter(orm.Recipe.meal_type == request.meal_type)
            
        candidates = query.all()
        if candidates:
            recipe_to_add = random.choice(candidates)
            
    if not recipe_to_add:
        # If explicit failed (not found) or random found nothing
        if request.recipe_id:
             raise HTTPException(status_code=404, detail="Recipe not found")
        # If random found nothing, just return plan unchanged for now
        return plan

    # Determine position (append)
    max_pos = -1
    for link in plan.plan_recipes:
        if link.position > max_pos:
            max_pos = link.position
            
    new_link = orm.MealPlanRecipe(
        plan_id=plan.id,
        recipe_id=recipe_to_add.id,
        position=max_pos + 1
    )
    db.add(new_link)
    
    # Invalidate lists
    plan.grocery_list = None
    plan.prep_plan = None
    plan.recipe_count += 1
    
    db.commit()
    db.refresh(plan)
    return plan

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
