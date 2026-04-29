import os

class TemplateEngine:
    """
    Renders templates by replacing placeholders with actual data.
    """
    
    def __init__(self, templates_dir):
        self.templates_dir = templates_dir

    def get_template_content(self, template_name):
        """Reads a template file from the templates directory."""
        path = os.path.join(self.templates_dir, template_name)
        if not os.path.exists(path):
            # Try adding .txt if it's missing
            if not template_name.endswith('.txt'):
                path += '.txt'
            
        if not os.path.exists(path):
            raise FileNotFoundError(f"Template '{template_name}' not found at {path}")
            
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def render(self, template_content, context):
        """
        Replaces placeholders in the format {key} with values from the context.
        Simple logic using string.format().
        """
        try:
            return template_content.format(**context)
        except KeyError as e:
            # If a key is missing, we might want to log it or handle it gracefully
            return template_content.replace(f"{{{e.args[0]}}}", "[MISSING DATA]")
