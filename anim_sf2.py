import bpy
import ast
import json
from mathutils import Vector
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper, ExportHelper


# Функция для импорта анимации
def import_bindec_animation(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            data = file.read()
    except UnicodeDecodeError:
        try:
            with open(filepath, 'r', encoding='latin1') as file:
                data = file.read()
        except UnicodeDecodeError:
            with open(filepath, 'rb') as file:
                data = file.read().decode('latin1', errors='ignore')

    frames = data.split("END")
    frames = [frame.strip() for frame in frames if frame.strip()]

    objects = []
    for i, frame_data in enumerate(frames):
        # Убираем начало строки с числом и квадратные скобки
        if "]" in frame_data:
            frame_data = frame_data.split("]", 1)[1].strip()

        blocks = frame_data.split("}{")
        blocks[0] = blocks[0].replace("{", "")
        blocks[-1] = blocks[-1].replace("}", "")

        # Создание пустышек для первых данных
        if i == 0:
            for j, block in enumerate(blocks):
                try:
                    coords = ast.literal_eval(f"({block})")
                    if len(coords) == 3:
                        x, y, z = coords
                        bpy.ops.object.empty_add(type='PLAIN_AXES', location=(x, y, z))
                        obj = bpy.context.object
                        obj.name = f"Empty_{j}"
                        obj["index"] = j  # Устанавливаем индекс объекта
                        objects.append(obj)
                except (ValueError, SyntaxError):
                    print(f"Ошибка обработки блока: {block}")

        else:
            # Обновление местоположений для последующих кадров
            for j, block in enumerate(blocks):
                try:
                    coords = ast.literal_eval(f"({block})")
                    if len(coords) == 3:
                        x, y, z = coords

                        # Поиск объекта по индексу
                        obj = next((o for o in objects if o["index"] == j), None)
                        if obj:
                            obj.location = (x, y, z)
                            obj.keyframe_insert(data_path="location", frame=i + 1)

                except (ValueError, SyntaxError):
                    print(f"Ошибка обработки блока: {block}")

    print(f"Анимация импортирована, количество кадров: {len(frames)}")


# Функция для экспорта анимации
def export_bindec_animation(filepath):
    # Загружаем форматы координат
    with open('coord_formats.json', 'r') as f:
        coord_formats = json.load(f)

    # Получаем все объекты с индексом и сортируем по имени
    objects = [obj for obj in bpy.data.objects if "index" in obj]
    objects.sort(key=lambda x: x["index"])  # Сортируем по индексу

    # Получаем диапазон кадров анимации
    start_frame = int(bpy.context.scene.frame_start)
    end_frame = int(bpy.context.scene.frame_end)

    with open(filepath, 'w', encoding='utf-8') as file:
        for frame in range(start_frame, end_frame + 1):
            bpy.context.scene.frame_set(frame)
            frame_coords = []
            for obj in objects:
                x, y, z = obj.location

                # Получаем формат для текущего объекта
                index = obj["index"]
                if index in coord_formats:
                    x_format, y_format, z_format = coord_formats[index]
                    coord_str = f"{{{x:.{x_format}f},{y:.{y_format}f},{z:.{z_format}f}}}"
                else:
                    # Если формат не найден, используем дефолтный формат
                    coord_str = f"{{{x:.6f},{y:.5f},{z:.6f}}}"

                frame_coords.append(coord_str)

            # Пишем количество точек перед координатами
            file.write(f"[{len(objects)}]{''.join(frame_coords)}END\n")

    print(f"Анимация экспортирована в файл: {filepath}")


# Функция для создания скелета из точек
def create_skeleton_from_points():
    objects = [obj for obj in bpy.data.objects if "index" in obj]
    objects.sort(key=lambda x: x["index"])

    # Создаем арматуру
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    armature = bpy.context.object
    armature.name = "Bindec_Skeleton"

    # Группируем точки по частям тела (примерно)
    bone_groups = {
        "Head": range(0, 5),  # Пример: точки 0-4 для головы
        "Left_Hand": range(5, 10),  # Пример: точки 5-9 для левой руки
        "Right_Hand": range(10, 15),  # Пример: точки 10-14 для правой руки
        "Body": range(15, 20),  # Пример: точки 15-19 для тела
        "Left_Leg": range(20, 25),  # Пример: точки 20-24 для левой ноги
        "Right_Leg": range(25, 30),  # Пример: точки 25-29 для правой ноги
    }

    # Создаем кости для каждой группы
    for bone_name, point_indices in bone_groups.items():
        # Находим среднюю точку для группы
        group_objects = [obj for obj in objects if obj["index"] in point_indices]
        if not group_objects:
            continue

        # Вычисляем среднее положение для кости
        avg_location = sum((obj.location for obj in group_objects), Vector((0, 0, 0))) / len(group_objects)

        # Создаем кость
        bone = armature.data.edit_bones.new(bone_name)
        bone.head = avg_location
        bone.tail = avg_location + Vector((0, 0, 1))  # Направление кости вдоль оси Z

        # Привязываем точки к кости
        for obj in group_objects:
            modifier = obj.modifiers.new(name="Armature", type='ARMATURE')
            modifier.object = armature
            vertex_group = obj.vertex_groups.new(name=bone_name)
            vertex_group.add([0], 1.0, 'REPLACE')  # Привязываем первую вершину (для пустышек)

    # Выходим из режима редактирования
    bpy.ops.object.mode_set(mode='OBJECT')


# Оператор для импорта
class ImportBindecAnimation(bpy.types.Operator, ImportHelper):
    bl_idname = "import_animation.bindec"
    bl_label = "Import Bindec Animation"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".bindec"

    filter_glob: StringProperty(
        default="*.bindec",
        options={'HIDDEN'},
        maxlen=255,
    )

    def execute(self, context):
        filepath = self.filepath
        import_bindec_animation(filepath)
        return {'FINISHED'}


# Оператор для экспорта
class ExportBindecAnimation(bpy.types.Operator, ExportHelper):
    bl_idname = "export_animation.bindec"
    bl_label = "Export Bindec Animation"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".bindec"

    filter_glob: StringProperty(
        default="*.bindec",
        options={'HIDDEN'},
        maxlen=255,
    )

    def execute(self, context):
        filepath = self.filepath
        export_bindec_animation(filepath)
        return {'FINISHED'}


# Оператор для создания скелета
class CreateSkeletonFromPoints(bpy.types.Operator):
    bl_idname = "create.skeleton_from_points"
    bl_label = "Create Skeleton from Points"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        create_skeleton_from_points()
        return {'FINISHED'}


# Панель для управления аддоном
class BindecAnimationPanel(bpy.types.Panel):
    bl_label = "Bindec Animation"
    bl_idname = "VIEW3D_PT_bindec_animation"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bindec"

    def draw(self, context):
        layout = self.layout
        layout.operator("import_animation.bindec", text="Import Animation")
        layout.operator("export_animation.bindec", text="Export Animation")
        layout.operator("create.skeleton_from_points", text="Create Skeleton")


# Регистрация классов
def register():
    bpy.utils.register_class(ImportBindecAnimation)
    bpy.utils.register_class(ExportBindecAnimation)
    bpy.utils.register_class(CreateSkeletonFromPoints)
    bpy.utils.register_class(BindecAnimationPanel)


# Отмена регистрации классов
def unregister():
    bpy.utils.unregister_class(ImportBindecAnimation)
    bpy.utils.unregister_class(ExportBindecAnimation)
    bpy.utils.unregister_class(CreateSkeletonFromPoints)
    bpy.utils.unregister_class(BindecAnimationPanel)


if __name__ == "__main__":
    register()