from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import auth
from django.contrib.auth import views as auth_views
from .forms import LoginForm, SignUpForm,QuizForm,QuestionForm,ChoiceForm
from django.contrib.auth.decorators import login_required
from .models import Quiz, Choice,QuizAnswer,QuizInformation
from django.db.models import Avg,Q
from django.contrib.auth.mixins import LoginRequiredMixin
# Create your views here.
def index(request):
    return render(request,"main/index.html")

def signup(request):
    if request.method == "GET":
        form = SignUpForm()
    elif request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password1"]#何故？#
            user = auth.authenticate(username=username,password=password)
            if user:
                auth.login(request, user)
            
            return redirect("index")
    context = {"form": form}
    return render(request,"main/signup.html",context)

class LoginView(auth_views.LoginView):
    authentication_form = LoginForm
    template_name= "main/login.html"

@login_required
def home(request):
    user = request.user
    quiz_list = Quiz.objects.filter(user=user)
    context = {
        "quiz_list":quiz_list,
    }
    return render(request, "main/home.html",context)


@login_required
def create_quiz(request):
    if request.method == "GET":
        quiz_form = QuizForm()
    elif request.method == "POST":
        quiz_form = QuizForm(request.POST)
        if quiz_form.is_valid():
            quiz = quiz_form.save(commit=False)
            user = request.user
            quiz.user = user
            #ここでquiz.user=request.userにしてもダメなのか#
            quiz.save()
            return redirect("create_question", quiz.id)
    context = {
        "quiz_form":quiz_form,
    }
    return render(request, "main/create_quiz.html", context)
    
@login_required
def create_question(request,quiz_id):

    quiz = get_object_or_404(Quiz, id=quiz_id)

    current_question_num = quiz.question_set.all().count()
    next_question_num = current_question_num + 1
    if request.method == "GET":
        question_form = QuestionForm()
        choice_form = ChoiceForm()
    
    elif request.method == "POST":
        question_form = QuestionForm(request.POST)
        choice_form = ChoiceForm()
        choices = request.POST.getlist("choice")
        answer_choice_num = request.POST["is_answer"]

        if question_form.is_valid():
            question = question_form.save(commit=False)
            question.quiz = quiz
            question.save()

            for i ,choice in enumerate(choices):

                if i == int(answer_choice_num):
                    Choice.objects.create(
                        question=question, choice=choice, is_answer = True
                )
                else:
                    Choice.objects.create(
                        question=question, choice=choice, is_answer = False
                )
            return redirect("create_question",quiz_id)
        
        
    context= {
        "question_form": question_form,
        "choice_form": choice_form,
        "quiz_id" : quiz_id,
        "next_question_num" : next_question_num,
    }

    return render(request,"main/create_question.html", context)



@login_required
def answer_quiz_list(request):
    user = request.user
    quiz_list = Quiz.objects.exclude(user=user)
    keyword = request.GET.get('keyword')
    if keyword:
        keywords = keyword.split()
        for k in keywords:
            quiz_list = quiz_list.filter(Q(title__icontains=keyword) | Q(description__icontains=keyword))
    context = {
        "quiz_list":quiz_list
    }
    return render(request,"main/answer_quiz_list.html",context)


@login_required
def answer_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.question_set.all()
    score = 0

    question_num = questions.count()
    user = request.user
    if request.method == "POST":
        for question in questions:
            choice_id = request.POST.get(str(question.id))
            choice_obj = get_object_or_404(Choice, id=choice_id)
            if choice_obj.is_answer:
                score += 1    
        answer_rate = score*100/question_num
        QuizAnswer.objects.create(
            user=user, quiz=quiz,score=score,answer_rate=answer_rate
        )
        # ユーザーが回答したクイズの情報を取得する
        quiz_answer = QuizAnswer.objects.filter(quiz=quiz)
        # 回答したクイズに対する全回答の平均得点の算出
        whole_average_score = quiz_answer.aggregate(Avg('score'))["score__avg"]
        # 回答したクイズに対する全回答の得点率の算出
        whole_answer_rate = quiz_answer.aggregate(Avg('answer_rate'))["answer_rate__avg"]

        # クイズ情報が存在すればユーザーが回答した分を含めて更新
        # 存在しなければ新しくクイズ情報を作成する
        QuizInformation.objects.update_or_create(
            quiz=quiz,
            defaults={
                "average_score":whole_average_score,
                "answer_rate":whole_answer_rate
            },
        )

        return redirect("result", quiz_id)
    context = {
        "quiz":quiz,
        "questions":questions,
    }
    return render(request, "main/answer_quiz.html",context)

@login_required
def quiz_information(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    quiz_information = QuizInformation.objects.filter(quiz=quiz).first()
    quiz_answer = quiz.quizanswer_set.all()
    context = {
        "quiz_answer":quiz_answer,
        "quiz_information":quiz_information,
    }
    return render(request, "main/quiz_information.html",context)



@login_required
def result(request,quiz_id):
    user = request.user
    quiz = get_object_or_404(Quiz, id=quiz_id)
    quiz_answer = QuizAnswer.objects.filter(quiz=quiz,user=user).order_by("answered_at").last()
    context = {
        "quiz_answer":quiz_answer,
    }

    return render(request, "main/result.html",context)

class LogoutView(auth_views.LogoutView,LoginRequiredMixin):
    pass