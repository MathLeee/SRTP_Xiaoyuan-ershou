from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SubmitField, FloatField
from wtforms.validators import DataRequired, Length, NumberRange

class ItemForm(FlaskForm):
    title = StringField('标题', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('描述', validators=[DataRequired(), Length(min=10)])
    price = FloatField('价格 (元)', validators=[DataRequired(), NumberRange(min=0.01, message='价格必须大于0')])
    image_file = FileField('商品图片', validators=[FileAllowed(['jpg', 'png', 'jpeg'], '仅支持图片文件 (jpg, png, jpeg)!')])
    submit = SubmitField('发布商品')


class MessageForm(FlaskForm):
    content = TextAreaField('消息内容', validators=[
        DataRequired(message='消息内容不能为空'),
        Length(min=1, max=1000, message='消息长度应在1-1000字符之间')
    ], render_kw={'placeholder': '输入您的消息...', 'rows': 3})
    submit = SubmitField('发送')