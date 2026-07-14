from django.contrib import admin

from .models import MasterCycle, TrophyAward, TriviaQuestion, TriviaSession, UserAnswer


admin.site.register(MasterCycle)
admin.site.register(TriviaSession)
admin.site.register(TriviaQuestion)
admin.site.register(UserAnswer)
admin.site.register(TrophyAward)
