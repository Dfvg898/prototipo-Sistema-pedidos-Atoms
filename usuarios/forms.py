from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator
from .models import Usuario, Repartidor


class LoginPersonalForm(forms.Form):
    correo = forms.EmailField(
        max_length=150,
        label="Correo electrónico",
        widget=forms.EmailInput(
            attrs={
                "id": "usuario",
                "class": "form-control",
                "placeholder": "ejemplo@sandwichsatoms.cl",
                "autocomplete": "username",
                "required": True,
            }
        ),
    )
    password = forms.CharField(
        max_length=128,
        label="Contraseña",
        widget=forms.PasswordInput(
            attrs={
                "id": "contrasena",
                "class": "form-control",
                "placeholder": "Ingresa tu contraseña",
                "autocomplete": "current-password",
                "required": True,
            }
        ),
    )

    def clean_correo(self):
        return self.cleaned_data["correo"].strip().lower()


class UsuarioCrearForm(forms.ModelForm):
    password = forms.CharField(
        max_length=128,
        label="Contraseña inicial (mín. 10 caracteres)",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = Usuario
        fields = ["nombre", "correo", "rol", "repartidor", "activo", "password"]

    def clean_correo(self):
        return self.cleaned_data["correo"].strip().lower()

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        rol = cleaned_data.get("rol")
        if rol != Usuario.Rol.REPARTIDOR:
            cleaned_data["repartidor"] = None
        return cleaned_data

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data["password"])
        usuario.is_staff = usuario.rol == Usuario.Rol.DUENO
        if commit:
            if usuario.rol == Usuario.Rol.REPARTIDOR and not usuario.repartidor:
                usuario.repartidor = Repartidor.objects.create(
                    nombre_repartidor=usuario.nombre,
                    activo=usuario.activo,
                )
            usuario.save()
            if usuario.repartidor and usuario.repartidor.activo != usuario.activo:
                usuario.repartidor.activo = usuario.activo
                usuario.repartidor.save(update_fields=["activo"])
        return usuario


class UsuarioEditarForm(forms.ModelForm):
    nueva_password = forms.CharField(
        max_length=128,
        required=False,
        label="Nueva contraseña (dejar en blanco para mantener la actual)",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = Usuario
        fields = ["nombre", "correo", "rol", "repartidor", "activo", "nueva_password"]

    def clean_correo(self):
        return self.cleaned_data["correo"].strip().lower()

    def clean_nueva_password(self):
        password = self.cleaned_data.get("nueva_password")
        if password:
            validate_password(password, self.instance)
        return password

    def clean(self):
        cleaned_data = super().clean()
        rol = cleaned_data.get("rol")
        if rol != Usuario.Rol.REPARTIDOR:
            cleaned_data["repartidor"] = None
        return cleaned_data

    def save(self, commit=True):
        usuario = super().save(commit=False)
        nueva_password = self.cleaned_data.get("nueva_password")
        if nueva_password:
            usuario.set_password(nueva_password)
        usuario.is_staff = usuario.rol == Usuario.Rol.DUENO
        if commit:
            if usuario.rol == Usuario.Rol.REPARTIDOR and not usuario.repartidor:
                usuario.repartidor = Repartidor.objects.create(
                    nombre_repartidor=usuario.nombre,
                    activo=usuario.activo,
                )
            usuario.save()
            if usuario.repartidor and usuario.repartidor.activo != usuario.activo:
                usuario.repartidor.activo = usuario.activo
                usuario.repartidor.save(update_fields=["activo"])
        return usuario


class RepartidorForm(forms.ModelForm):
    class Meta:
        model = Repartidor
        fields = ["nombre_repartidor", "telefono", "activo"]

    def save(self, commit=True):
        repartidor = super().save(commit=commit)
        if commit and hasattr(repartidor, "cuenta_usuario") and repartidor.cuenta_usuario:
            if repartidor.cuenta_usuario.activo != repartidor.activo:
                repartidor.cuenta_usuario.activo = repartidor.activo
                repartidor.cuenta_usuario.save(update_fields=["activo"])
        return repartidor


validador_telefono = RegexValidator(
    regex=r"^\+?[0-9\s\-]{8,20}$",
    message="Ingresa un número de teléfono válido (mínimo 8 dígitos).",
)


class DatosEntregaCheckoutForm(forms.Form):
    MODALIDAD_RETIRO = "RETIRO"
    MODALIDAD_DESPACHO = "DESPACHO"
    MODALIDADES = [
        (MODALIDAD_RETIRO, "Retiro en local"),
        (MODALIDAD_DESPACHO, "Despacho a domicilio"),
    ]
    COSTO_DESPACHO_FIJO = 2000

    nombre_cliente = forms.CharField(
        max_length=100,
        required=True,
        label="Nombre completo *",
        error_messages={"required": "El nombre completo es obligatorio."},
        widget=forms.TextInput(
            attrs={
                "id": "nombre",
                "class": "form-control",
                "placeholder": "Ej. Camila Rojas",
            }
        ),
    )
    telefono = forms.CharField(
        max_length=20,
        required=True,
        validators=[validador_telefono],
        label="Teléfono de contacto *",
        error_messages={"required": "El teléfono de contacto es obligatorio."},
        widget=forms.TextInput(
            attrs={
                "id": "telefono",
                "type": "tel",
                "class": "form-control",
                "placeholder": "+56 9 1234 5678",
            }
        ),
    )
    modalidad_entrega = forms.ChoiceField(
        choices=MODALIDADES,
        initial=MODALIDAD_RETIRO,
        required=True,
        error_messages={"required": "Debes seleccionar una modalidad de entrega."},
    )
    direccion = forms.CharField(
        max_length=200,
        required=False,
        label="Dirección de entrega *",
        widget=forms.TextInput(
            attrs={
                "id": "direccion",
                "class": "form-control",
                "placeholder": "Calle, número y sector",
            }
        ),
    )
    referencia = forms.CharField(
        max_length=200,
        required=False,
        label="Referencia de la dirección",
        widget=forms.TextInput(
            attrs={
                "id": "referencia",
                "class": "form-control",
                "placeholder": "Ej. Casa azul, frente a la plaza",
            }
        ),
    )
    observaciones = forms.CharField(
        max_length=250,
        required=False,
        label="Observaciones o comentarios especiales del pedido",
        widget=forms.Textarea(
            attrs={
                "id": "indicaciones",
                "class": "form-control",
                "rows": 3,
                "maxlength": 250,
                "placeholder": "Ej. Sin mayonesa en el segundo sándwich, cortar en mitades, tocar timbre fuerte...",
            }
        ),
    )

    def clean_nombre_cliente(self):
        valor = self.cleaned_data.get("nombre_cliente", "").strip()
        if not valor:
            raise forms.ValidationError("El nombre completo es obligatorio.")
        return valor

    def clean_telefono(self):
        return self.cleaned_data.get("telefono", "").strip()

    def clean_observaciones(self):
        return self.cleaned_data.get("observaciones", "").strip()

    def clean(self):
        cleaned_data = super().clean()
        modalidad = cleaned_data.get("modalidad_entrega")
        direccion = (cleaned_data.get("direccion") or "").strip()
        referencia = (cleaned_data.get("referencia") or "").strip()

        if modalidad == self.MODALIDAD_DESPACHO:
            if not direccion:
                self.add_error(
                    "direccion",
                    "La dirección de entrega es obligatoria cuando eliges despacho a domicilio.",
                )
            cleaned_data["direccion"] = direccion
            cleaned_data["referencia"] = referencia
            cleaned_data["costo_despacho"] = self.COSTO_DESPACHO_FIJO
        else:
            cleaned_data["direccion"] = ""
            cleaned_data["referencia"] = ""
            cleaned_data["costo_despacho"] = 0

        for field_name in self.errors:
            if field_name in self.fields:
                clases = self.fields[field_name].widget.attrs.get("class", "form-control")
                if "is-invalid" not in clases:
                    self.fields[field_name].widget.attrs["class"] = f"{clases} is-invalid"

        return cleaned_data
