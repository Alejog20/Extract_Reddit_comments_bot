Extractor de Datos de Reddit sobre Aranceles Comerciales
Este proyecto consiste en una herramienta de extracción de datos de Reddit para analizar las reacciones y discusiones sobre los aranceles del 25% impuestos por la administración Trump a México y Canadá. Utiliza la API REST de Reddit directamente mediante solicitudes HTTP, evitando dependencias como PRAW.
🌟 Características

Extracción de posts y comentarios de múltiples subreddits
Búsqueda por términos específicos relacionados con aranceles comerciales
Autenticación OAuth2 con la API oficial de Reddit
Limpieza automática de textos para análisis posterior
Guardado de resultados en CSV con codificación adecuada
Compatible con Google Colab para análisis interactivo
Interfaz de usuario en terminal para fácil personalización

📋 Requisitos

Python 3.6 o superior
Bibliotecas: requests, pandas, datetime, re, csv, json, base64, urllib
Credenciales de API de Reddit (Client ID y Client Secret)
Para usar en Google Colab: acceso a Google Drive

🔧 Configuración
Obtener credenciales de Reddit:

Visita https://www.reddit.com/prefs/apps
Haz clic en "crear una aplicación" en la parte inferior
Completa la información:

Nombre: ArancelesAnalysis (o el que prefieras)
Tipo: Script
Descripción: Extractor de datos para análisis de aranceles
URL sobre la app: (puede dejarse en blanco)
URI de redirección: http://localhost:8080


Al crear la aplicación, obtendrás el Client ID (debajo del nombre) y Client Secret

🚀 Uso
En Google Colab:

Abre el notebook en Google Colab
Ejecuta todas las celdas en orden
Introduce las credenciales de la API cuando se soliciten
Personaliza los términos de búsqueda y subreddits si lo deseas
Los datos se guardarán en la ruta especificada de Google Drive

Localmente:

Clona este repositorio
Instala las dependencias: pip install -r requirements.txt
Ejecuta el script: python reddit_extractor.py
Sigue las instrucciones en pantalla para ingresar tus credenciales y personalizar la búsqueda

📊 Estructura de Datos
Posts:

post_id: Identificador único del post
title: Título del post
text: Contenido del post
score: Puntuación (upvotes - downvotes)
upvote_ratio: Proporción de votos positivos
created_utc: Fecha de creación
num_comments: Número de comentarios
permalink: Enlace permanente al post
subreddit: Comunidad donde se publicó
author: Autor del post
search_term: Término usado para encontrar este post
title_clean: Versión limpia del título (sin URLs, caracteres especiales, etc.)
text_clean: Versión limpia del contenido

Comentarios:

comment_id: Identificador único del comentario (generado internamente)
post_id: ID del post al que pertenece
text: Texto del comentario
score: Puntuación del comentario
created_utc: Fecha de creación
author: Autor del comentario
is_submitter: Indica si es el autor del post original
permalink: Enlace permanente al comentario
text_clean: Versión limpia del texto

📁 Almacenamiento
Por defecto, los datos se guardan en:
Copiar/content/drive/MyDrive/Development/DataScience/Sentiment_Analysis/
Los archivos generados son:

reddit_posts_aranceles_YYYYMMDD_HHMM.csv: Posts extraídos
reddit_comments_aranceles_YYYYMMDD_HHMM.csv: Comentarios extraídos

⚠️ Limitaciones

API de Reddit: Limite de 60 solicitudes por minuto
El script incluye pausas para respetar estos límites
La búsqueda está limitada a términos específicos y no recopila todos los posts de un subreddit

🔍 Términos de búsqueda predeterminados

"aranceles México"
"aranceles Canadá"
"Trump aranceles"
"25% arancel"
"TMEC aranceles"
"tariffs Mexico Canada"

🌐 Subreddits predeterminados

Economics
Politics
worldnews
news
business
mexico
canada
trade

📊 Posibles análisis
Con los datos obtenidos se puede realizar:

Análisis de sentimiento sobre los aranceles
Identificación de temas principales mediante modelado de tópicos
Análisis comparativo entre la percepción de los aranceles a México vs. Canadá
Evolución temporal de las reacciones
Correlación entre sentimiento y puntuación de los posts/comentarios

🤝 Contribuciones
Las contribuciones son bienvenidas. Por favor, abre un issue primero para discutir los cambios que te gustaría realizar.
