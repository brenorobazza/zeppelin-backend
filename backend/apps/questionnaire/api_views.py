from .models import (
    AdoptedLevel,
    Statement,
    FeedbackQuestionnaire,
    Questionnaire,
    QuestionnaireExcel,
    Answer,
)
from .serializers import (
    AdoptedLevelReadSerializer,
    AdoptedLevelWriteSerializer,
    StatementReadSerializer,
    StatementWriteSerializer,
    FeedbackQuestionnaireReadSerializer,
    FeedbackQuestionnaireWriteSerializer,
    QuestionnaireReadSerializer,
    QuestionnaireWriteSerializer,
    QuestionnaireExcelReadSerializer,
    QuestionnaireExcelWriteSerializer,
    AnswerReadSerializer,
    AnswerWriteSerializer,
)
from .analytics import QuestionnaireAnalyticsService

from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from oauth2_provider.contrib.rest_framework import (
    OAuth2Authentication,
)
from rest_framework.authentication import SessionAuthentication
from .pagination import CustomPagination
from rest_framework import filters
from rest_framework.response import Response
from rest_framework.views import APIView
import django_filters.rest_framework
from django.core.exceptions import ValidationError


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # Para não bloquear chamadas da API do Frontend React


class AdoptedLevelViewSet(ModelViewSet):
    queryset = AdoptedLevel.objects.all()
    pagination_class = CustomPagination
    # As respostas sao por organizacao, entao exigimos autenticacao.
    authentication_classes = [OAuth2Authentication, CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = (
        filters.SearchFilter,
        filters.OrderingFilter,
        django_filters.rest_framework.DjangoFilterBackend,
    )
    filterset_fields = "__all__"
    search_fields = ["percentage"]
    ordering_fields = "percentage"
    ordering = ["id"]

    def get_serializer_class(self):
        if self.request.method in ["GET"]:
            return AdoptedLevelReadSerializer
        return AdoptedLevelWriteSerializer


class StatementViewSet(ModelViewSet):
    queryset = Statement.objects.all()
    pagination_class = CustomPagination
    authentication_classes = [OAuth2Authentication, CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = (
        filters.SearchFilter,
        filters.OrderingFilter,
        django_filters.rest_framework.DjangoFilterBackend,
    )
    filterset_fields = "__all__"
    search_fields = ["code", "statement"]
    ordering_fields = "__all__"
    ordering = ["id"]

    def get_serializer_class(self):
        if self.request.method in ["GET"]:
            return StatementReadSerializer
        return StatementWriteSerializer


class FeedbackQuestionnaireViewSet(ModelViewSet):
    queryset = FeedbackQuestionnaire.objects.all()
    pagination_class = CustomPagination
    authentication_classes = [OAuth2Authentication, CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = (
        filters.SearchFilter,
        filters.OrderingFilter,
        django_filters.rest_framework.DjangoFilterBackend,
    )
    filterset_fields = "__all__"
    search_fields = ["collected_date"]
    ordering_fields = "__all__"
    ordering = ["id"]

    def get_serializer_class(self):
        if self.request.method in ["GET"]:
            return FeedbackQuestionnaireReadSerializer
        return FeedbackQuestionnaireWriteSerializer


class QuestionnaireViewSet(ModelViewSet):
    queryset = Questionnaire.objects.all()
    pagination_class = CustomPagination
    authentication_classes = [OAuth2Authentication, CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = (
        filters.SearchFilter,
        filters.OrderingFilter,
        django_filters.rest_framework.DjangoFilterBackend,
    )
    filterset_fields = ["applied_date"]
    search_fields = ["applied_date"]
    ordering_fields = ["applied_date"]
    ordering = ["id"]

    def get_serializer_class(self):
        if self.request.method in ["GET"]:
            return QuestionnaireReadSerializer
        return QuestionnaireWriteSerializer


class QuestionnaireExcelViewSet(ModelViewSet):
    queryset = QuestionnaireExcel.objects.all()
    pagination_class = CustomPagination
    authentication_classes = [OAuth2Authentication, CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = (
        filters.SearchFilter,
        filters.OrderingFilter,
        django_filters.rest_framework.DjangoFilterBackend,
    )
    filterset_fields = ["applied_date"]
    search_fields = ["applied_date"]
    ordering_fields = ["applied_date"]
    ordering = ["id"]

    def get_serializer_class(self):
        if self.request.method in ["GET"]:
            return QuestionnaireExcelReadSerializer
        return QuestionnaireExcelWriteSerializer


class AnswerViewSet(ModelViewSet):
    queryset = Answer.objects.all()
    pagination_class = CustomPagination
    authentication_classes = [OAuth2Authentication, CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = (
        filters.SearchFilter,
        filters.OrderingFilter,
        django_filters.rest_framework.DjangoFilterBackend,
    )
    filterset_fields = "__all__"
    search_fields = ["comment"]
    ordering_fields = "__all__"
    ordering = ["id"]

    def get_serializer_class(self):
        if self.request.method in ["GET"]:
            return AnswerReadSerializer
        return AnswerWriteSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        statement_answer = serializer.validated_data.get("statement_answer")
        organization_answer = serializer.validated_data.get("organization_answer")
        adopted_level_answer = serializer.validated_data.get("adopted_level_answer")
        comment_answer = serializer.validated_data.get("comment_answer", "")
        questionnaire_answer = serializer.validated_data.get(
            "questionnaire_answer", None
        )

        answer, created = Answer.objects.update_or_create(
            statement_answer=statement_answer,
            organization_answer=organization_answer,
            questionnaire_answer=questionnaire_answer,
            defaults={
                "adopted_level_answer": adopted_level_answer,
                "comment_answer": comment_answer,
            },
        )

        return Response(
            self.get_serializer(answer).data, status=201 if created else 200
        )


# As views abaixo expõem a camada analítica como endpoints REST.
# Cada endpoint alimenta diretamente uma tela do frontend.
class QuestionnaireDashboardAnalyticsView(APIView):
    authentication_classes = [OAuth2Authentication, CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Encaminha a requisicao para o servico de analytics e devolve o payload pronto.
        service = QuestionnaireAnalyticsService()
        try:
            payload = service.get_dashboard_payload(request)
        except ValidationError as exc:
            return Response({"error": exc.message}, status=400)
        return Response(payload)


# Endpoint da tela de resultados detalhados.
class QuestionnaireResultsAnalyticsView(APIView):
    authentication_classes = [OAuth2Authentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        service = QuestionnaireAnalyticsService()
        try:
            payload = service.get_results_payload(request)
        except ValidationError as exc:
            return Response({"error": exc.message}, status=400)
        return Response(payload)


# Endpoint da tela de recomendacoes/roadmap.
class QuestionnaireRecommendationsAnalyticsView(APIView):
    authentication_classes = [OAuth2Authentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        service = QuestionnaireAnalyticsService()
        try:
            payload = service.get_recommendations_payload(request)
        except ValidationError as exc:
            return Response({"error": exc.message}, status=400)
        return Response(payload)


# Endpoint da tela de historico/evolucao.
class QuestionnaireHistoryAnalyticsView(APIView):
    authentication_classes = [OAuth2Authentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        service = QuestionnaireAnalyticsService()
        try:
            payload = service.get_history_payload(request)
        except ValidationError as exc:
            return Response({"error": exc.message}, status=400)
        return Response(payload)


# Endpoint agregado para comparacao de ciclos e benchmarks.
class QuestionnaireComparisonAnalyticsView(APIView):
    authentication_classes = [OAuth2Authentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        service = QuestionnaireAnalyticsService()
        try:
            payload = service.get_comparison_payload(request)
        except ValidationError as exc:
            return Response({"error": exc.message}, status=400)
        return Response(payload)


# Endpoint agregado para benchmark de peer group externo.
class QuestionnaireBenchmarkAnalyticsView(APIView):
    authentication_classes = [OAuth2Authentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        service = QuestionnaireAnalyticsService()
        try:
            payload = service.get_benchmark_payload(request)
        except ValidationError as exc:
            return Response({"error": exc.message}, status=400)
        return Response(payload)
