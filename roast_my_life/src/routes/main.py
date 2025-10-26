from flask import Blueprint, render_template
from src.services.video_service import fetch_videos, transform_videos_for_template

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def home() -> str:
    """
    Render the home page with welcome text.

    Returns:
        str: Rendered HTML template for the home page.
    """
    return render_template('index.html')


@main_bp.route('/form')
def form_page() -> str:
    """
    Render the form page with dynamic video selection grid.

    Returns:
        str: Rendered HTML template for the form page.
    """
    videos = fetch_videos()
    template_videos = transform_videos_for_template(videos)
    return render_template('form.html', videos=template_videos)
