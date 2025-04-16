from django.shortcuts import get_object_or_404, redirect
from api.constants import CUR_BASE_URL
from api.models import Recipe


def redirect_to_recipe(request, short_url):
    recipe = get_object_or_404(Recipe, short_url=short_url)
    return redirect(f'{CUR_BASE_URL}recipes/{recipe.pk}')
