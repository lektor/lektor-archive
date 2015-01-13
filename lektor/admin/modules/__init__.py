def register_modules(app):
    from lektor.admin.modules import panel
    app.register_blueprint(panel.bp)
