# ruff: noqa: E501

# deleted_from = {
#     "authorOf": {
#         "IRI": "https://dblp.org/rdf/schema#authorOf",
#         "description": "The creator is the author of the publication.",
#     },
#     "creatorOf": {
#         "IRI": "https://dblp.org/rdf/schema#creatorOf",
#         "description": "The creator of the publication.",
#     },
#     "editorOf": {
#         "IRI": "https://dblp.org/rdf/schema#editorOf",
#         "description": "The creator is the editor of the publication.",
#     },
# }

PROPERTIES_URI_AND_DESCRIPTION = {
    "affiliation": {
        "IRI": "https://dblp.org/rdf/schema#affiliation",
        "description": "A (past or present) affiliation of the creator. (Remark: This property currently just gives literal xsd:string values until institutions are modelled as proper entities.)",
    },
    "archivedWebpage": {
        "IRI": "https://dblp.org/rdf/schema#archivedWebpage",
        "description": "The URL of an archived web page about this item, which may no longer be available in the web.",
    },
    "authoredBy": {
        "IRI": "https://dblp.org/rdf/schema#authoredBy",
        "description": "The publication is authored by the creator.",
    },
    "awardwebpage": {
        "IRI": "https://dblp.org/rdf/schema#awardWebpage",
        "description": "The URL of a web page about an award received by this creator.",
    },
    "bibtexType": {
        "IRI": "https://dblp.org/rdf/schema#bibtexType",
        "description": "The bibtex type of the publication, e.g., book, inproceedings, etc.",
    },
    "coAuthorWith": {
        "IRI": "https://dblp.org/rdf/schema#coAuthorWith",
        "description": "The creator is co-author with the other creator.",
    },
    "coCreatorWith": {
        "IRI": "https://dblp.org/rdf/schema#coCreatorWith",
        "description": "The creator is co-creator with the other creator.",
    },
    "coEditorWith": {
        "IRI": "https://dblp.org/rdf/schema#coEditorWith",
        "description": "The creator is co-editor with the other creator.",
    },
    "createdBy": {
        "IRI": "https://dblp.org/rdf/schema#createdBy",
        "description": "The publication is created by the creator.",
    },
    "creatorname": {
        "IRI": "https://dblp.org/rdf/schema#creatorName",
        "description": "The full name of the creator.",
    },
    "creatorNote": {
        "IRI": "https://dblp.org/rdf/schema#creatorNote",
        "description": "An additional note about the creator.",
    },
    "documentPage": {
        "IRI": "https://dblp.org/rdf/schema#documentPage",
        "description": "The URL of the electronic edition of the publication.",
    },
    "doi": {
        "IRI": "https://dblp.org/rdf/schema#doi",
        "description": "A Digital Object Identifier.",
    },
    "editedBy": {
        "IRI": "https://dblp.org/rdf/schema#editedBy",
        "description": "The publication is edited by the creator.",
    },
    "formerStreamTitle": {
        "IRI": "https://dblp.org/rdf/schema#formerStreamTitle",
        "description": "A former title of the stream.",
    },
    "hasSignature": {
        "IRI": "https://dblp.org/rdf/schema#hasSignature",
        "description": "A signature that links this publication to an creator.",
    },
    "hasVersion": {
        "IRI": "https://dblp.org/rdf/schema#hasVersion",
        "description": "The publication has a different, more specific (instance) publication as its version.",
    },
    "homepage": {
        "IRI": "https://dblp.org/rdf/schema#homepage",
        "description": "The URL of an academic homepage of this creator.",
    },
    "homonymousCreator": {
        "IRI": "https://dblp.org/rdf/schema#homonymousCreator",
        "description": "This creator shares a homonymous name with the other creator.",
    },
    "identifier": {
        "IRI": "https://dblp.org/rdf/schema#identifier",
        "description": "An abstract identifier.",
    },
    "indexPage": {
        "IRI": "https://dblp.org/rdf/schema#indexPage",
        "description": "The URL of the dblp stream index page for this stream.",
    },
    "isVersion": {
        "IRI": "https://dblp.org/rdf/schema#isVersion",
        "description": "The publication is a version of another, more general (concept) publication.",
    },
    "isVersionOf": {
        "IRI": "https://dblp.org/rdf/schema#isVersionOf",
        "description": "The publication is a version of another, more general (concept) publication.",
    },
    "isbn": {
        "IRI": "https://dblp.org/rdf/schema#isbn",
        "description": "An International Standard Book Number.",
    },
    "iso4": {
        "IRI": "https://dblp.org/rdf/schema#iso4",
        "description": "The stream's ISO4 abbreviation.",
    },
    "issn": {
        "IRI": "https://dblp.org/rdf/schema#issn",
        "description": "An International Standard Serial Number.",
    },
    "listedOnTocPage": {
        "IRI": "https://dblp.org/rdf/schema#listedOnTocPage",
        "description": "The url of the dblp table of contents page listing this publication.",
    },
    "monthOfPublication": {
        "IRI": "https://dblp.org/rdf/schema#monthOfPublication",
        "description": "The month the publication has been published.",
    },
    "numberOfCreators": {
        "IRI": "https://dblp.org/rdf/schema#numberOfCreators",
        "description": "The number of creators who created this publication.",
    },
    "omid": {
        "IRI": "https://dblp.org/rdf/schema#omid",
        "description": "An OpenCitations Meta Identifier.",
    },
    "orcid": {
        "IRI": "https://dblp.org/rdf/schema#orcid",
        "description": "An Open Researcher and Contributor ID.",
    },
    "pagination": {
        "IRI": "https://dblp.org/rdf/schema#pagination",
        "description": "The page numbers where the publication can be found.",
    },
    "possibleActualCreator": {
        "IRI": "https://dblp.org/rdf/schema#possibleActualCreator",
        "description": "This ambiguous creator may be (or may be not) just a disambiguation proxy for the other creator. Further actual creator candidates are possible.",
    },
    "predecessorStream": {
        "IRI": "https://dblp.org/rdf/schema#predecessorStream",
        "description": "This stream is a predecessor of the other stream.",
    },
    "primaryAffiliation": {
        "IRI": "https://dblp.org/rdf/schema#primaryAffiliation",
        "description": "The primary affiliation of the creator. (Remark: This property currently just gives literal xsd:string values until institutions are modelled as proper entities.)",
    },
    "primaryCreatorName": {
        "IRI": "https://dblp.org/rdf/schema#primaryCreatorName",
        "description": "The primary full name of the creator.",
    },
    "primaryDocumentPage": {
        "IRI": "https://dblp.org/rdf/schema#primaryDocumentPage",
        "description": "The primary URL of the electronic edition of the publication.",
    },
    "primaryHomepage": {
        "IRI": "https://dblp.org/rdf/schema#primaryHomepage",
        "description": "The primary URL of an academic homepage of this creator.",
    },
    "primaryStreamTitle": {
        "IRI": "https://dblp.org/rdf/schema#primaryStreamTitle",
        "description": "The primary title of the stream.",
    },
    "proxyAmbiguousCreator": {
        "IRI": "https://dblp.org/rdf/schema#proxyAmbiguousCreator",
        "description": "This creator (and any of her fellow homonymous creators) is also represented by the given ambiguous creator in cases where the authorship of a publication is undetermined.",
    },
    "publicationNote": {
        "IRI": "https://dblp.org/rdf/schema#publicationNote",
        "description": "An additional note to the publication.",
    },
    "publishedAsPartOf": {
        "IRI": "https://dblp.org/rdf/schema#publishedAsPartOf",
        "description": "The publication has been published as a part of the other publication.",
    },
    "publishedBy": {
        "IRI": "https://dblp.org/rdf/schema#publishedBy",
        "description": "The publisher of the publication. (Remark: This property currently just gives literal xsd:string values until publishers are modelled as proper entities.)",
    },
    "publishedIn": {
        "IRI": "https://dblp.org/rdf/schema#publishedIn",
        "description": "The name of the series, the journal, or the book in which the publication has been published. (Remark: This property currently just gives literal xsd:string values until journals and conference series are modelled as proper entities.)",
    },
    "publishedInBook": {
        "IRI": "https://dblp.org/rdf/schema#publishedInBook",
        "description": "The name of the book in which the publication has been published. (Remark: This is currently an intermediate property that will be removed once journals and conference series are modelled as proper entities.)",
    },
    "publishedInBookChapter": {
        "IRI": "https://dblp.org/rdf/schema#publishedInBookChapter",
        "description": "The chapter of the book in which the publication has been published. (Remark: This is currently an intermediate property that will be removed once journals and conference series are modelled as proper entities.)",
    },
    "publishedInJournal": {
        "IRI": "https://dblp.org/rdf/schema#publishedInJournal",
        "description": "The name of the journal in which the publication has been published. (Remark: This is currently an intermediate property that will be removed once journals and conference series are modelled as proper entities.)",
    },
    "publishedInJournalVolume": {
        "IRI": "https://dblp.org/rdf/schema#publishedInJournalVolume",
        "description": "The volume of the journal in which the publication has been published. (Remark: This is currently an intermediate property that will be removed once journals and conference series are modelled as proper entities.)",
    },
    "publishedInJournalIssue": {
        "IRI": "https://dblp.org/rdf/schema#publishedInJournalVolumeIssue",
        "description": "The issue of the journal in which the publication has been published. (Remark: This is currently an intermediate property that will be removed once journals and conference series are modelled as proper entities.)",
    },
    "publishedInSeries": {
        "IRI": "https://dblp.org/rdf/schema#publishedInSeries",
        "description": "The name of the series in which the publication has been published. (Remark: This is currently an intermediate property that will be removed once journals and conference series are modelled as proper entities.)",
    },
    "publishedInSeriesVolume": {
        "IRI": "https://dblp.org/rdf/schema#publishedInSeriesVolume",
        "description": "The volume of the series in which the publication has been published. (Remark: This is currently an intermediate property that will be removed once journals and conference series are modelled as proper entities.)",
    },
    "publishedInStream": {
        "IRI": "https://dblp.org/rdf/schema#publishedInStream",
        "description": "The conference series, the journal, or the repository in which the publication has been published.",
    },
    "publishersAddress": {
        "IRI": "https://dblp.org/rdf/schema#publishersAddress",
        "description": "The address of the publisher. (Remark: This is currently an intermediate property that will be removed once publishers are modelled as proper entities.)",
    },
    "relatedStream": {
        "IRI": "https://dblp.org/rdf/schema#relatedStream",
        "description": "This stream is related to the other stream in some unspecified way.",
    },
    "signatureCreator": {
        "IRI": "https://dblp.org/rdf/schema#signatureCreator",
        "description": "A linked creator of the publication.",
    },
    "signatureDblpName": {
        "IRI": "https://dblp.org/rdf/schema#signatureDblpName",
        "description": "A dblp name (including any possible trailing homonym number) that links the publication to a creator.",
    },
    "signatureOrcid": {
        "IRI": "https://dblp.org/rdf/schema#signatureOrcid",
        "description": "An ORCID that links the publication to a creator.",
    },
    "signatureOrdinal": {
        "IRI": "https://dblp.org/rdf/schema#signatureOrdinal",
        "description": "The ordinal number of this signature for the publication, starting with 1.",
    },
    "signaturePublication": {
        "IRI": "https://dblp.org/rdf/schema#signaturePublication",
        "description": "The publication of this signature.",
    },
    "streamTitle": {
        "IRI": "https://dblp.org/rdf/schema#streamTitle",
        "description": "A title of the stream.",
    },
    "subStream": {
        "IRI": "https://dblp.org/rdf/schema#subStream",
        "description": "This stream is (or was) a part of the other stream.",
    },
    "successorStream": {
        "IRI": "https://dblp.org/rdf/schema#successorStream",
        "description": "This stream is a successor of the other stream.",
    },
    "superStream": {
        "IRI": "https://dblp.org/rdf/schema#superStream",
        "description": "This stream has (or had) the other stream as a part.",
    },
    "thesisAcceptedBySchool": {
        "IRI": "https://dblp.org/rdf/schema#thesisAcceptedBySchool",
        "description": "The school where the publication (typically a thesis) has been accepted. (Remark: This property currently just gives literal xsd:string values until institutions are modelled as proper entities.)",
    },
    "title": {
        "IRI": "https://dblp.org/rdf/schema#title",
        "description": "The title of the publication.",
    },
    "versionConcept": {
        "IRI": "https://dblp.org/rdf/schema#versionConcept",
        "description": "The linked general (concept) publication.",
    },
    "versionInstance": {
        "IRI": "https://dblp.org/rdf/schema#versionInstance",
        "description": "The linked specific (instance) publication version.",
    },
    "versionLabel": {
        "IRI": "https://dblp.org/rdf/schema#versionLabel",
        "description": "The human-readable version label of the specific (instance) publication version.",
    },
    "versionOrdinal": {
        "IRI": "https://dblp.org/rdf/schema#versionOrdinal",
        "description": "The ordinal number of the specific (instance) publication version. This number is solely intended for sorting purposes: bigger numbers indicate later versions. Version ordinals do not need to describe a complete number range, nor is there a necessary relationship to the version labels.",
    },
    "versionUri": {
        "IRI": "https://dblp.org/rdf/schema#versionUri",
        "description": "An (optional) URI of identifying the linked specific (instance) publication version.",
    },
    "webpage": {
        "IRI": "https://dblp.org/rdf/schema#webpage",
        "description": "The URL of a web page about this item.",
    },
    "wikidata": {
        "IRI": "https://dblp.org/rdf/schema#wikidata",
        "description": "A wikidata item.",
    },
    "wikipedia": {
        "IRI": "https://dblp.org/rdf/schema#wikipedia",
        "description": "The URL of an (English) Wikipedia article about this item.",
    },
    "yearOfEvent": {
        "IRI": "https://dblp.org/rdf/schema#yearOfEvent",
        "description": "The year the conference or workshop contribution has been presented.",
    },
    "yearOfPublication": {
        "IRI": "https://dblp.org/rdf/schema#yearOfPublication",
        "description": "The year the publication's issue or volume has been published.",
    },
}