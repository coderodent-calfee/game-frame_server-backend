from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import HttpResponse, Http404
from .models import Image
from .serializers import ImageSerializer
import base64
from django.utils.html import escape

@api_view(['GET'])
def image_list(request):
    """
    Return a list of all images in the database.
    """
    images = Image.objects.all()
    serializer = ImageSerializer(images, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def image_detail(request, image_id):
    """
    Return raw image bytes, or HTML with metadata if ?html=1 is passed.
    """
    try:
        image = Image.objects.get(id=image_id)
    except Image.DoesNotExist:
        raise Http404("Image not found")

    html_mode = request.query_params.get('html') == '1'

    if html_mode:
        metadata = f"""
            <ul>
                <li>ID: {image.id}</li>
                <li>Uploader: {image.uploader.id if image.uploader else 'None'}</li>
                <li>Type: {escape(image.type)}</li>
                <li>Private: {image.private}</li>
                <li>Created at: {image.created_at}</li>
            </ul>
        """

        if image.type == 'svg':
            # Embed SVG inline
            img_tag = image.data.decode('utf-8')
        else:
            # Convert PNG/JPG to base64 for embedding
            import base64
            img_b64 = base64.b64encode(image.data).decode('utf-8')
            img_tag = f'<img src="data:image/{image.type};base64,{img_b64}" width="300"/>'

        html = f"<html><body>{img_tag}{metadata}</body></html>"
        return HttpResponse(html, content_type='text/html')

    else:
        content_type = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'svg': 'image/svg+xml'
        }.get(image.type, 'application/octet-stream')
        return HttpResponse(image.data, content_type=content_type)

@api_view(['GET'])
def image_single_info(request, image_id):
    """
    Return metadata + base64 image data for a single image by ID.
    """
    try:
        img = Image.objects.get(id=image_id)
    except Image.DoesNotExist:
        raise Http404("Image not found")

    data_base64 = base64.b64encode(img.data).decode('utf-8') if img.data else None

    result = {
        "id": str(img.id),
        "uploader": img.uploader.id if img.uploader else None,
        "type": img.type,
        "private": img.private,
        "created_at": img.created_at,
        "data_base64": data_base64
    }

    return Response(result)