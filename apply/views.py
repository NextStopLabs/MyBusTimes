from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Position, Application

def home(request):
    positions = Position.objects.filter(available_places__gt=0).order_by("-created_at")
    return render(request, "apply_home.html", {"positions": positions})

@login_required
def apply_position(request, position_id):
    position = get_object_or_404(Position, pk=position_id)

    if request.method == "POST":
        # Get the details from the form
        details = request.POST.get("details", "").strip()

        # Collect answers for each question
        question_answers = {}
        for idx, question in enumerate(position.initial_questions.splitlines(), start=1):
            key = f"question_{idx}"
            question_answers[question] = request.POST.get(key, "").strip()

        # Save application
        Application.objects.create(
            applicant=request.user,
            position=position,
            details=details,
            question_answers=question_answers,
            status="pending"
        )

        return redirect("home")  # Redirect after applying

    # Show form with questions
    questions = [q.strip() for q in position.initial_questions.splitlines() if q.strip()]
    return render(request, "apply_position.html", {
        "position": position,
        "questions": questions
    })
