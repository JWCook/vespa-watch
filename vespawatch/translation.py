from modeltranslation.translator import register, TranslationOptions
from vespawatch.models import Taxon, IdentificationCard, ManagementActionProblem


@register(Taxon)
class SpeciesTranslationOptions(TranslationOptions):
    fields = ('vernacular_name',)


@register(IdentificationCard)
class IdentificationCardTranslationOptions(TranslationOptions):
    fields = ('description',)


@register(ManagementActionProblem)
class ManagementActionProblemTranslationOptions(TranslationOptions):
    fields = ('description',)
