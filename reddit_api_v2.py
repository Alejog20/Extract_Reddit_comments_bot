import requests
import pandas as pd
import datetime
import time
import re
import csv
import json
import base64
import os
from urllib.parse import quote
import logging
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.live import Live

# Initialize Rich Console
console = Console()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]  # Solo mostramos en consola para Google Colab
)
logger = logging.getLogger(__name__)

def get_reddit_token(client_id, client_secret):
    """
    Obtiene un token de autenticación de Reddit usando OAuth
    """
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "User-Agent": "RedditDataExtractor/1.0"
    }
    data = {
        "grant_type": "client_credentials"
    }

    with Live(console=console, screen=False, auto_refresh=True, transient=True) as live:
        live.update("[bold yellow]Attempting to get Reddit authentication token...[/bold yellow]", refresh=True)
        try:
            response = requests.post(
                "https://www.reddit.com/api/v1/access_token",
                headers=headers,
                data=data
            )

            if response.status_code == 200:
                live.update("[bold green]Reddit authentication token obtained successfully.[/bold green]")
                return response.json().get("access_token")
            else:
                live.update("[bold red]Error obtaining token.[/bold red]")
                logger.error(f"Error obtaining token: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
        except Exception as e:
            live.update("[bold red]Error in token request.[/bold red]")
            logger.error(f"Error in token request: {e}")
            return None

def get_post_metrics(post_data):
    """
    Extrae métricas objetivas de un post
    """
    # Texto del post (título + contenido)
    title = post_data.get("title", "")
    selftext = post_data.get("selftext", "")
    
    # Métricas objetivas (sin análisis de contenido)
    metrics = {
        # Estadísticas básicas
        "title_length": len(title),
        "text_length": len(selftext),
        "total_length": len(title + " " + selftext),
        "word_count": len((title + " " + selftext).split()),
        
        # Métricas de engagement
        "upvote_ratio": post_data.get("upvote_ratio", 0),
        "score": post_data.get("score", 0),
        "num_comments": post_data.get("num_comments", 0),
        
        # Características objetivas
        "has_url": 1 if "http" in (title + " " + selftext) else 0,
        "is_self": post_data.get("is_self", True),
        "is_video": post_data.get("is_video", False),
        "is_stickied": post_data.get("stickied", False),
        "domain": post_data.get("domain", ""),
    }
    
    return metrics

def get_comment_metrics(comment_data):
    """
    Extrae métricas objetivas de un comentario
    """
    # Texto del comentario
    text = comment_data.get("body", "")
    
    # Métricas objetivas (sin análisis de contenido)
    metrics = {
        # Estadísticas básicas
        "text_length": len(text),
        "word_count": len(text.split()),
        
        # Métricas de engagement
        "score": comment_data.get("score", 0),
        "controversiality": comment_data.get("controversiality", 0),
        
        # Características objetivas
        "has_url": 1 if "http" in text else 0,
        "is_submitter": comment_data.get("is_submitter", False),
        "is_stickied": comment_data.get("stickied", False),
        "depth": comment_data.get("depth", 0),
    }
    
    return metrics

def search_reddit(token, query, subreddit, limit=25, sort="relevance"):
    """
    Busca posts en Reddit usando la API REST
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "RedditDataExtractor/1.0"
    }

    encoded_query = quote(query)

    if subreddit.lower() == 'all':
        url = f"https://oauth.reddit.com/search?q={encoded_query}&sort={sort}&limit={limit}"
    else:
        url = f"https://oauth.reddit.com/r/{subreddit}/search?q={encoded_query}&sort={sort}&restrict_sr=1&limit={limit}"

    try:
        # Mantenemos la verificación HTTP normal
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            return data.get("data", {}).get("children", [])
        else:
            logger.error(f"Error en la búsqueda: {response.status_code}")
            logger.error(f"Respuesta: {response.text}")
            return []
    except Exception as e:
        logger.error(f"Error en la solicitud de búsqueda: {e}")
        return []

def get_comments(token, post_id, limit=25):
    """
    Obtiene los comentarios de un post específico
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "RedditDataExtractor/1.0"
    }

    url = f"https://oauth.reddit.com/comments/{post_id}?limit={limit}"

    try:
        # Mantenemos la verificación HTTP normal
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            if len(data) >= 2:  # El segundo elemento contiene los comentarios
                return data[1].get("data", {}).get("children", [])
            return []
        else:
            logger.error(f"Error obteniendo comentarios: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error en la solicitud de comentarios: {e}")
        return []

def extract_reddit_data(client_id, client_secret, search_terms, subreddits, post_limit=25, comment_limit=25):
    """
    Extrae datos de Reddit basados en términos de búsqueda y subreddits
    sin realizar análisis de contenido
    """
    # Obtener token de autenticación
    token = get_reddit_token(client_id, client_secret)
    if not token:
        logger.error("Failed to obtain authentication token. Please verify your credentials.")
        return pd.DataFrame(), pd.DataFrame()

    logger.info("Authentication successful with Reddit API.")

    all_posts = []
    all_comments = []
    comment_id = 0
    subreddit_list = subreddits.split('+')

    total_tasks = len(search_terms) * len(subreddit_list)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        main_task = progress.add_task("[green]Extracting Reddit data...[/green]", total=total_tasks)

        # Procesa cada término de búsqueda
        for term in search_terms:
            for subreddit in subreddit_list:
                progress.update(main_task, description=f"[green]Searching for '{term}' in r/{subreddit}...[/green]")
                logger.info(f"Searching for '{term}' in r/{subreddit}")

                posts = search_reddit(token, term, subreddit, limit=post_limit)

                for post_data in posts:
                    post = post_data.get("data", {})

                    # Extrae información del post
                    post_id = post.get("id")

                    # Evita duplicados
                    if any(p.get("post_id") == post_id for p in all_posts):
                        continue

                    # Obtener métricas objetivas
                    post_metrics = get_post_metrics(post)

                    # Extrae datos del post
                    post_info = {
                        "post_id": post_id,
                        "title": post.get("title", ""),
                        "text": post.get("selftext", ""),
                        "score": post.get("score", 0),
                        "upvote_ratio": post.get("upvote_ratio", 0),
                        "created_utc": datetime.datetime.fromtimestamp(post.get("created_utc", 0)),
                        "num_comments": post.get("num_comments", 0),
                        "permalink": f"https://www.reddit.com{post.get('permalink', '')}",
                        "subreddit": post.get("subreddit", ""),
                        "author": post.get("author", "[deleted]"),
                        "search_term": term,
                        # Campos adicionales de las métricas objetivas
                        "title_length": post_metrics["title_length"],
                        "text_length": post_metrics["text_length"],
                        "total_length": post_metrics["total_length"],
                        "word_count": post_metrics["word_count"],
                        "has_url": post_metrics["has_url"],
                        "is_self": post_metrics["is_self"],
                        "is_video": post_metrics["is_video"],
                        "is_stickied": post_metrics["is_stickied"],
                        "domain": post_metrics["domain"],
                    }

                    all_posts.append(post_info)

                    # Obtiene comentarios
                    if post.get("num_comments", 0) > 0:
                        comments = get_comments(token, post_id, limit=comment_limit)

                        for comment_data in comments:
                            comment = comment_data.get("data", {})

                            # Ignora entradas que no son comentarios reales
                            if comment.get("body") is None or comment.get("id") is None:
                                continue

                            # Obtener métricas objetivas del comentario
                            comment_metrics = get_comment_metrics(comment)

                            comment_info = {
                                "comment_id": comment_id,
                                "post_id": post_id,
                                "text": comment.get("body", ""),
                                "score": comment.get("score", 0),
                                "created_utc": datetime.datetime.fromtimestamp(comment.get("created_utc", 0)),
                                "author": comment.get("author", "[deleted]"),
                                "is_submitter": comment.get("is_submitter", False),
                                "permalink": f"https://www.reddit.com{comment.get('permalink', '')}",
                                # Campos adicionales de las métricas objetivas
                                "text_length": comment_metrics["text_length"],
                                "word_count": comment_metrics["word_count"],
                                "has_url": comment_metrics["has_url"],
                                "is_submitter": comment_metrics["is_submitter"],
                                "is_stickied": comment_metrics["is_stickied"],
                                "depth": comment_metrics["depth"],
                                "controversiality": comment_metrics["controversiality"],
                            }

                            all_comments.append(comment_info)
                            comment_id += 1

                    # Pausa para evitar límites de tasa
                    time.sleep(1)

                # Pausa entre subreddits
                time.sleep(2)
                progress.update(main_task, advance=1)

    # Convierte a DataFrames
    df_posts = pd.DataFrame(all_posts) if all_posts else pd.DataFrame()
    df_comments = pd.DataFrame(all_comments) if all_comments else pd.DataFrame()

    logger.info(f"Found {len(df_posts)} posts and {len(df_comments)} comments.")

    return df_posts, df_comments

def clean_text(text):
    """
    Limpia el texto de caracteres especiales y formatos Reddit
    sin alterar el contenido semántico
    """
    if not isinstance(text, str):
        return ""

    # Elimina URLs
    text = re.sub(r'http\S+', '', text)
    # Elimina caracteres de formato Reddit
    text = re.sub(r'\[|\]|\(|\)|\*|#|>', '', text)
    # Normaliza espacios
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def save_to_csv(df, filename):
    """Guarda un DataFrame en un archivo CSV manejando errores de codificación"""
    if df.empty:
        logger.warning(f"No hay datos para guardar en {filename}")
        return False

    try:
        df.to_csv(filename, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
        logger.info(f"Data saved to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error guardando {filename}: {e}")
        # Intenta con otra codificación
        try:
            df.to_csv(filename, index=False, encoding='latin1', quoting=csv.QUOTE_ALL)
            logger.info(f"Data saved to {filename} with alternative encoding")
            return True
        except Exception as e2:
            logger.error(f"Could not save {filename}: {e2}")
            return False



def get_user_inputs():
    """Solicita al usuario las entradas necesarias para la extracción de datos"""
    console.print("\n" + "="*60)
    console.print("[bold green]REDDIT DATA EXTRACTOR[/bold green]", justify="center")
    console.print("="*60 + "\n")

    console.print("To use this script, you need Reddit application credentials.")
    console.print("You can create an app here: [link=https://www.reddit.com/prefs/apps]https://www.reddit.com/prefs/apps[/link]\n")

    # Solicita credenciales
    client_id = input("Client ID for your Reddit app: ").strip()
    client_secret = input("Client Secret for your Reddit app: ").strip()

    # Solicita términos de búsqueda
    default_terms = []

    console.print("\n[bold]Default search terms:[/bold]")
    for i, term in enumerate(default_terms, 1):
        console.print(f"  {i}. {term}")

    custom_terms = input("\nDo you want to use custom search terms? (y/n, default: n): ").strip().lower()

    if custom_terms in ['s', 'si', 'sí', 'y', 'yes']:
        terms_input = input("Enter terms separated by commas: ").strip()
        search_terms = [term.strip() for term in terms_input.split(',') if term.strip()]
        if not search_terms:
            logger.warning("No valid terms entered. Using default terms.")
            search_terms = default_terms
    else:
        search_terms = default_terms

    # Solicita subreddits
    default_subreddits = ""

    custom_subreddits = input(f"\nDo you want to use custom subreddits? (y/n, default: n): ").strip().lower()

    if custom_subreddits in ['s', 'si', 'sí', 'y', 'yes']:
        subreddits = input(f"Enter subreddits separated by '+': ").strip()
        if not subreddits:
            logger.warning("No valid subreddits entered. Using default subreddits.")
            subreddits = default_subreddits
    else:
        subreddits = default_subreddits

    # Límites
    try:
        post_limit = int(input("\nMaximum number of posts per term and subreddit (default: 25): ") or "25")
    except ValueError:
        post_limit = 25
        logger.warning("Invalid value. Using 25 posts per term and subreddit.")

    try:
        comment_limit = int(input("Maximum number of comments per post (default: 20): ") or "20")
    except ValueError:
        comment_limit = 20
        logger.warning("Invalid value. Using 20 comments per post.")

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "search_terms": search_terms,
        "subreddits": subreddits,
        "post_limit": post_limit,
        "comment_limit": comment_limit
    }

def main():
    # Define local directory for saving data
    save_path = './reddit_data'
    if not os.path.exists(save_path):
        os.makedirs(save_path)
        logger.info(f"Local directory created: {save_path}")
    
    # Obtener entradas del usuario
    inputs = get_user_inputs()

    console.print("\n" + "-"*60)
    logger.info(f"Starting Reddit data extraction from r/{inputs['subreddits']}")
    logger.info(f"Searching for {len(inputs['search_terms'])} terms: {', '.join(inputs['search_terms'])}")
    console.print("-"*60 + "\n")

    # Extrae los datos
    df_posts, df_comments = extract_reddit_data(
        client_id=inputs["client_id"],
        client_secret=inputs["client_secret"],
        search_terms=inputs["search_terms"],
        subreddits=inputs["subreddits"],
        post_limit=inputs["post_limit"],
        comment_limit=inputs["comment_limit"]
    )

    logger.info("Extraction completed.")
    logger.info(f"Posts extracted: {len(df_posts)}")
    logger.info(f"Comments extracted: {len(df_comments)}")

    # Limpia los textos si hay datos
    if not df_posts.empty:
        df_posts['title_clean'] = df_posts['title'].apply(clean_text)
        df_posts['text_clean'] = df_posts['text'].apply(clean_text)

    if not df_comments.empty:
        df_comments['text_clean'] = df_comments['text'].apply(clean_text)

    # Crear timestamp para los nombres de archivo
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")

    # Guardar los dataframes en Google Drive
    if not df_posts.empty:
        posts_filename = os.path.join(save_path, f"reddit_posts_data_{timestamp}.csv")
        save_to_csv(df_posts, posts_filename)

    if not df_comments.empty:
        comments_filename = os.path.join(save_path, f"reddit_comments_data_{timestamp}.csv")
        save_to_csv(df_comments, comments_filename)

    logger.info(f"Process completed. Files saved to: {save_path}")

if __name__ == "__main__":
    main()