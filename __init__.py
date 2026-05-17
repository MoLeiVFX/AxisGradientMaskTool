# 轴向渐变遮罩工具插件
# Axis Gradient Mask Tool
# 适用于 Blender 3.6 及以上版本

bl_info = {
    "name": "Axis Gradient Mask Tool",
    "author": "墨泪MoLei_VFX",
    "version": (1, 0),
    "blender": (3, 6, 0),
    "location": "3D View > Sidebar > AGMT",
    "description": "根据模型在世界空间中的位置沿指定轴向生成渐变遮罩，烘焙到UV并导出为图像",
    "category": "Import-Export",
}

ADDON_VERSION = "1.0"

import bpy
import os
import re
import ast
from mathutils import Vector

ADDON_TRANSLATIONS = {}

def load_po_translations(language="en"):
    po_path = os.path.join(os.path.dirname(__file__), "locales", language, "LC_MESSAGES", f"{language}.po")
    if not os.path.exists(po_path):
        return {}

    translations = {}
    msgid = None
    msgstr = None
    active = None

    def append_po_text(value, text):
        try:
            parsed = ast.literal_eval(text)
        except (SyntaxError, ValueError):
            parsed = text.strip('"')
        return (value or "") + parsed

    def commit_entry():
        if msgid and msgstr:
            translations[msgid] = msgstr

    with open(po_path, "r", encoding="utf-8") as po_file:
        for raw_line in po_file:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("msgid "):
                commit_entry()
                msgid = append_po_text("", line[6:].strip())
                msgstr = ""
                active = "msgid"
            elif line.startswith("msgstr "):
                msgstr = append_po_text("", line[7:].strip())
                active = "msgstr"
            elif line.startswith('"') and active == "msgid":
                msgid = append_po_text(msgid, line)
            elif line.startswith('"') and active == "msgstr":
                msgstr = append_po_text(msgstr, line)

    commit_entry()
    return translations

def build_blender_translations(translations):
    locale_entries = {("*", msgid): msgstr for msgid, msgstr in translations.items()}
    return {
        "en": locale_entries,
        "en_US": locale_entries,
        "en_GB": locale_entries,
    }

def register_translations():
    global ADDON_TRANSLATIONS
    ADDON_TRANSLATIONS = load_po_translations("en")
    if ADDON_TRANSLATIONS:
        try:
            bpy.app.translations.unregister(__name__)
        except RuntimeError:
            pass
        bpy.app.translations.register(__name__, build_blender_translations(ADDON_TRANSLATIONS))

def unregister_translations():
    try:
        bpy.app.translations.unregister(__name__)
    except RuntimeError:
        pass

def is_english_ui():
    language = getattr(bpy.context.preferences.view, "language", "")
    return language in {"en_US", "en_GB", "en"} or language.startswith("en_")

def translate_text(text):
    translated = bpy.app.translations.pgettext_iface(text)
    if translated == text and is_english_ui():
        translated = ADDON_TRANSLATIONS.get(text, text)
    return translated

_ = translate_text

def get_gradient_material(obj):
    mat_name = f"GradientMask_Material_{obj.name}"
    return bpy.data.materials.get(mat_name)

def get_gradient_ramp_node(obj):
    mat = get_gradient_material(obj)
    if not mat or not mat.use_nodes:
        return None
    return mat.node_tree.nodes.get("GradientMask_ColorRamp")

def capture_color_ramp(ramp):
    return {
        "interpolation": ramp.interpolation,
        "elements": [
            (element.position, tuple(element.color))
            for element in ramp.elements
        ]
    }

def restore_color_ramp(ramp, ramp_data):
    while len(ramp.elements) > 2:
        ramp.elements.remove(ramp.elements[-1])

    elements = sorted(ramp_data["elements"], key=lambda item: item[0])
    ramp.interpolation = ramp_data["interpolation"]
    ramp.elements[0].position = elements[0][0]
    ramp.elements[0].color = elements[0][1]
    ramp.elements[1].position = elements[1][0]
    ramp.elements[1].color = elements[1][1]

    for position, color in elements[2:]:
        element = ramp.elements.new(position)
        element.color = color

def sync_scene_from_ramp(scene, ramp_node):
    ramp = ramp_node.color_ramp
    if len(ramp.elements) < 2:
        return
    scene.gradient_black_position = ramp.elements[0].position
    scene.gradient_white_position = ramp.elements[1].position
    scene.gradient_black_color = ramp.elements[0].color[:3]
    scene.gradient_white_color = ramp.elements[1].color[:3]

def update_gradient_preview(self, context):
    obj = context.active_object
    if not obj or obj.type != 'MESH':
        return
    apply_gradient_material(
        obj,
        context.scene.gradient_axis,
        context.scene.gradient_invert
    )

def make_unique_export_path(export_path):
    directory = os.path.dirname(export_path)
    base_name = os.path.splitext(os.path.basename(export_path))[0]
    extension = os.path.splitext(export_path)[1] or ".png"

    unique_path = export_path
    index = 1
    while os.path.exists(unique_path):
        unique_path = os.path.join(directory, f"{base_name}_{index:03d}{extension}")
        index += 1
    return unique_path

def apply_gradient_material(obj, axis, invert_gradient, black_position=None, white_position=None, black_color=None, white_color=None, bake_image=None):
    # 计算物体在世界空间中的最小和最大坐标
    world_verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    if not world_verts:
        return False, _("模型没有顶点")

    if axis == 'X':
        values = [v.x for v in world_verts]
    elif axis == 'Y':
        values = [v.y for v in world_verts]
    else:
        values = [v.z for v in world_verts]

    min_val = min(values)
    max_val = max(values)
    range_val = max_val - min_val
    if range_val == 0:
        range_val = 1.0

    existing_ramp_node = get_gradient_ramp_node(obj)
    if existing_ramp_node and len(existing_ramp_node.color_ramp.elements) >= 2:
        existing_ramp = existing_ramp_node.color_ramp
        ramp_data = capture_color_ramp(existing_ramp)
    else:
        black_position = 0.0 if black_position is None else black_position
        white_position = 1.0 if white_position is None else white_position
        black_color = (0.0, 0.0, 0.0) if black_color is None else black_color
        white_color = (1.0, 1.0, 1.0) if white_color is None else white_color
        ramp_data = {
            "interpolation": 'LINEAR',
            "elements": [
                (black_position, (black_color[0], black_color[1], black_color[2], 1.0)),
                (white_position, (white_color[0], white_color[1], white_color[2], 1.0)),
            ]
        }

    mat = get_gradient_material(obj)
    if not mat:
        mat = bpy.data.materials.new(name=f"GradientMask_Material_{obj.name}")

    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    geometry_node = nodes.new(type='ShaderNodeNewGeometry')
    geometry_node.location = (-900, 120)

    separate_node = nodes.new(type='ShaderNodeSeparateXYZ')
    separate_node.location = (-700, 120)

    map_node = nodes.new(type='ShaderNodeMapRange')
    map_node.location = (-500, 120)
    map_node.clamp = True
    map_node.inputs['From Min'].default_value = max_val if invert_gradient else min_val
    map_node.inputs['From Max'].default_value = min_val if invert_gradient else max_val
    map_node.inputs['To Min'].default_value = 0.0
    map_node.inputs['To Max'].default_value = 1.0

    ramp_node = nodes.new(type='ShaderNodeValToRGB')
    ramp_node.name = "GradientMask_ColorRamp"
    ramp_node.label = "GradientMask_ColorRamp"
    ramp_node.location = (-260, 120)
    ramp = ramp_node.color_ramp
    restore_color_ramp(ramp, ramp_data)

    emit_node = nodes.new(type='ShaderNodeEmission')
    emit_node.location = (0, 120)

    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (240, 120)

    links.new(geometry_node.outputs['Position'], separate_node.inputs['Vector'])
    links.new(separate_node.outputs[axis], map_node.inputs['Value'])
    links.new(map_node.outputs['Result'], ramp_node.inputs['Fac'])
    links.new(ramp_node.outputs['Color'], emit_node.inputs['Color'])
    links.new(emit_node.outputs['Emission'], output_node.inputs['Surface'])

    if bake_image:
        tex_node = nodes.new(type='ShaderNodeTexImage')
        tex_node.image = bake_image
        tex_node.name = "GradientMask_BakeTarget"
        tex_node.label = "GradientMask_BakeTarget"
        tex_node.location = (-260, -160)
        tex_node.select = True
        tex_node.interpolation = 'Closest'
        nodes.active = tex_node

    if len(obj.data.materials) > 0:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

    obj.active_material = mat
    return True, ""

class OBJECT_OT_PreviewGradientMask(bpy.types.Operator):
    """预览定向溶解遮罩"""
    bl_idname = "object.preview_gradient_mask"
    bl_label = "预览遮罩"
    bl_description = "预览当前遮罩"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        obj = context.active_object

        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, _("请选择一个网格对象"))
            return {'CANCELLED'}

        success, message = apply_gradient_material(
            obj,
            scene.gradient_axis,
            scene.gradient_invert,
            scene.gradient_black_position,
            scene.gradient_white_position,
            scene.gradient_black_color,
            scene.gradient_white_color
        )
        if not success:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}

        ramp_node = get_gradient_ramp_node(obj)
        if ramp_node:
            sync_scene_from_ramp(scene, ramp_node)

        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'MATERIAL'

        self.report({'INFO'}, _("已更新渐变材质预览"))
        return {'FINISHED'}

class OBJECT_OT_ExportGradientMask(bpy.types.Operator):
    """导出定向溶解遮罩"""
    bl_idname = "object.export_gradient_mask"
    bl_label = "导出遮罩"
    bl_description = "生成并导出遮罩"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        obj = context.active_object

        # 检查是否选中了网格对象
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, _("请选择一个网格对象"))
            return {'CANCELLED'}

        # 获取用户设置的参数
        axis = scene.gradient_axis
        resolution_x = scene.gradient_resolution_x
        resolution_y = scene.gradient_resolution_y
        custom_name = scene.gradient_export_name.strip()
        color_depth = scene.gradient_color_depth
        sample_count = scene.gradient_sample_count
        use_float_buffer = scene.gradient_use_float
        use_anti_aliasing = scene.gradient_use_aa
        invert_gradient = scene.gradient_invert
        black_position = scene.gradient_black_position
        white_position = scene.gradient_white_position
        black_color = scene.gradient_black_color
        white_color = scene.gradient_white_color
        
        # 检查是否有UV层
        if not obj.data.uv_layers:
            self.report({'ERROR'}, _("该模型没有UV层，请先展开UV"))
            return {'CANCELLED'}

        # 保存当前状态
        original_engine = scene.render.engine
        original_samples = scene.cycles.samples
        original_use_denoising = scene.cycles.use_denoising
        original_active_object = context.view_layer.objects.active
        selected_objects = context.selected_objects.copy()
        
        # 保存图像颜色深度设置
        original_color_depth = None
        if hasattr(scene.render, 'image_settings'):
            original_color_depth = scene.render.image_settings.color_depth

        try:
            # 设置 Cycles 为渲染引擎
            scene.render.engine = 'CYCLES'
            
            # 设置采样数以获得更高质量的烘焙
            scene.cycles.samples = sample_count
            scene.cycles.use_denoising = False  # 烘焙遮罩不需要降噪
            
            # 生成图像名称
            if custom_name:
                # 清理文件名（移除非法字符）
                custom_name = re.sub(r'[<>:"/\\|?*]', '_', custom_name)
                image_name = custom_name
            else:
                # 默认使用模型名称+轴向
                axis_names = {'X': _("X轴"), 'Y': _("Y轴"), 'Z': _("Z轴")}
                image_name = f"{obj.name}_{axis_names[axis]}{_('渐变遮罩')}"

            # 导出图像路径。若文件已存在，自动追加序号，避免覆盖已有遮罩。
            export_path = scene.gradient_export_path
            if not export_path:
                if bpy.data.filepath:
                    export_dir = os.path.dirname(bpy.data.filepath)
                else:
                    export_dir = os.path.expanduser("~")
                export_path = os.path.join(export_dir, f"{image_name}.png")
            else:
                if os.path.isdir(export_path):
                    export_path = os.path.join(export_path, f"{image_name}.png")
                else:
                    export_dir = os.path.dirname(export_path)
                    if export_dir:
                        os.makedirs(export_dir, exist_ok=True)
                    if not export_path.lower().endswith('.png'):
                        export_path += '.png'

            export_path = make_unique_export_path(export_path)
            image_name = os.path.splitext(os.path.basename(export_path))[0]
            
            # 创建高精度图像
            # 使用浮点缓冲区
            img = bpy.data.images.new(
                name=image_name, 
                width=resolution_x, 
                height=resolution_y, 
                alpha=True, 
                float_buffer=use_float_buffer,  # 使用浮点缓冲区
                is_data=False,
                stereo3d=False,
                tiled=False
            )
            
            # 设置图像颜色为全黑
            img.generated_color = (0.0, 0.0, 0.0, 1.0)
            img.generated_type = 'BLANK'
            
            # 设置图像颜色深度（仅在导出时生效）
            if hasattr(img, 'color_space_settings'):
                img.colorspace_settings.name = 'Non-Color'
            
            # 强制更新图像数据
            img.update()

            # 创建材质节点渐变，并把图像纹理节点设为烘焙目标
            success, message = apply_gradient_material(
                obj,
                axis,
                invert_gradient,
                black_position,
                white_position,
                black_color,
                white_color,
                bake_image=img
            )
            if not success:
                self.report({'ERROR'}, message)
                return {'CANCELLED'}

            # 选择物体并设置为活动对象
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj

            # 设置烘焙参数
            scene.cycles.bake_type = 'EMIT'
            
            # 设置烘焙选项以提高质量
            if hasattr(scene.render, 'bake'):
                if hasattr(scene.render.bake, 'use_pass_direct'):
                    scene.render.bake.use_pass_direct = False
                if hasattr(scene.render.bake, 'use_pass_indirect'):
                    scene.render.bake.use_pass_indirect = False
                if hasattr(scene.render.bake, 'use_pass_color'):
                    scene.render.bake.use_pass_color = True
                if hasattr(scene.render.bake, 'margin'):
                    scene.render.bake.margin = 16
                if hasattr(scene.render.bake, 'target'):
                    scene.render.bake.target = 'IMAGE_TEXTURES'
                if hasattr(scene.render.bake, 'use_clear'):
                    scene.render.bake.use_clear = True
                if hasattr(scene.render.bake, 'use_selected_to_active'):
                    scene.render.bake.use_selected_to_active = False
            
            # 设置抗锯齿选项（如果存在）
            if hasattr(scene.cycles, 'use_baking_aa') and use_anti_aliasing:
                scene.cycles.use_baking_aa = True

            # 确保图像有数据（使用浮点精度初始化）
            if use_float_buffer:
                # 对于浮点图像，使用浮点值初始化
                img.pixels = [0.0] * (resolution_x * resolution_y * 4)
            else:
                # 对于8位图像，使用整数初始化
                img.pixels = [0.0] * (resolution_x * resolution_y * 4)
            img.update()

            # 执行烘焙
            try:
                bpy.ops.object.bake(type='EMIT')
                self.report({'INFO'}, _("烘焙完成 (采样数: %d)") % sample_count)
            except Exception as e:
                self.report({'ERROR'}, _("烘焙失败: %s") % str(e))
                return {'CANCELLED'}
            
            # 设置导出图像的颜色深度
            if hasattr(scene.render, 'image_settings'):
                scene.render.image_settings.color_depth = color_depth
                scene.render.image_settings.color_mode = 'RGBA'
                scene.render.image_settings.compression = 15  
            
            # 保存图像
            img.filepath_raw = export_path
            img.file_format = 'PNG'
            img.save()

            # 获取文件大小信息
            file_size = os.path.getsize(export_path) if os.path.exists(export_path) else 0
            size_mb = file_size / (1024 * 1024)
            
            self.report({'INFO'}, _("遮罩已导出到: %s (大小: %.2fMB)") % (export_path, size_mb))
            
        except Exception as e:
            self.report({'ERROR'}, _("执行失败: %s") % str(e))
            return {'CANCELLED'}
            
        finally:
            # 恢复原始状态
            scene.render.engine = original_engine
            scene.cycles.samples = original_samples
            scene.cycles.use_denoising = original_use_denoising
            if original_color_depth and hasattr(scene.render, 'image_settings'):
                scene.render.image_settings.color_depth = original_color_depth
            context.view_layer.objects.active = original_active_object
            for sel_obj in selected_objects:
                sel_obj.select_set(True)

        return {'FINISHED'}

class VIEW3D_PT_GradientMaskPanel(bpy.types.Panel):
    """3D视图侧边栏面板 - 轴向渐变遮罩工具"""
    bl_label = "轴向渐变遮罩工具"
    bl_idname = "VIEW3D_PT_gradient_mask"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AGMT"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # 轴向选择
        box = layout.box()
        box.label(text="渐变方向:", icon='AXIS_TOP')
        row = box.row(align=True)
        row.prop(scene, "gradient_axis", expand=True)
        box.prop(scene, "gradient_invert", text="反转黑白渐变")
        box.label(text="渐变色标:", icon='COLOR')
        obj = context.active_object
        ramp_node = get_gradient_ramp_node(obj) if obj and obj.type == 'MESH' else None
        if ramp_node:
            box.template_color_ramp(ramp_node, "color_ramp", expand=True)
        else:
            box.label(text="先点击预览当前遮罩生成颜色渐变节点", icon='INFO')

        # 分辨率设置
        box = layout.box()
        box.label(text="输出分辨率:", icon='IMAGE_DATA')
        col = box.column(align=True)
        col.prop(scene, "gradient_resolution_x", text="宽度")
        col.prop(scene, "gradient_resolution_y", text="高度")
        
        # 精度设置
        box = layout.box()
        box.label(text="精度设置:", icon='SETTINGS')
        
        # 颜色深度
        col = box.column(align=True)
        col.prop(scene, "gradient_color_depth", text="色彩深度")
        
        # 采样数
        col = box.column(align=True)
        col.prop(scene, "gradient_sample_count", text="烘焙采样数")
        
        # 高级选项
        col = box.column(align=True)
        col.prop(scene, "gradient_use_float", text="使用浮点缓冲(16位)")
        col.prop(scene, "gradient_use_aa", text="启用抗锯齿")
        
        # 显示精度说明
        if scene.gradient_color_depth == '8':
            box.label(text="8位: 256级灰度", icon='INFO')
        elif scene.gradient_color_depth == '16':
            box.label(text="16位: 65536级灰度", icon='INFO')
        else:
            box.label(text="32位: 42亿级灰度", icon='INFO')

        # 导出设置
        box = layout.box()
        box.label(text="导出设置:", icon='EXPORT')
        
        # 导出命名选项
        col = box.column(align=True)
        col.prop(scene, "gradient_export_name", text="文件名")
        if not scene.gradient_export_name:
            # 显示默认命名预览
            if context.active_object and context.active_object.type == 'MESH':
                obj = context.active_object
                axis_names = {'X': _("X轴"), 'Y': _("Y轴"), 'Z': _("Z轴")}
                default_name = f"{obj.name}_{axis_names[scene.gradient_axis]}{_('渐变遮罩')}.png"
                col.label(text=f"{_('默认')}: {default_name}", icon='INFO')
        
        # 导出路径
        col = box.column(align=True)
        col.prop(scene, "gradient_export_path", text="保存位置")
        
        # 如果路径为空，显示默认路径预览
        if not scene.gradient_export_path and bpy.data.filepath:
            default_dir = os.path.dirname(bpy.data.filepath)
            col.label(text=f"{_('默认目录')}: {default_dir}", icon='FILE_FOLDER')

        # 导出按钮
        layout.separator()
        preview_row = layout.row(align=True)
        preview_row.scale_y = 1.5
        
        # 根据是否有活动对象启用/禁用预览按钮
        if context.active_object and context.active_object.type == 'MESH':
            preview_row.operator("object.preview_gradient_mask", text=_("预览当前遮罩"), icon='HIDE_OFF')
        else:
            preview_row.operator("object.preview_gradient_mask", text=_("请选择网格对象"), icon='ERROR')
            preview_row.enabled = False

        row = layout.row(align=True)
        row.scale_y = 2.0
        
        # 根据是否有活动对象启用/禁用按钮
        if context.active_object and context.active_object.type == 'MESH':
            row.operator("object.export_gradient_mask", text=_("生成并导出遮罩"), icon='RENDER_STILL')
        else:
            row.operator("object.export_gradient_mask", text=_("请选择网格对象"), icon='ERROR')
            row.enabled = False

        layout.separator()
        info_box = layout.box()
        info_box.label(text=_("版本信息:"), icon='INFO')
        info_col = info_box.column(align=True)
        info_lines = [
            f"{_('插件版本')}: v{ADDON_VERSION}",
            f"{_('作者')}: {_('墨泪')}",
            f"{_('主页')}: https://www.kiiiii.com",
        ]
        for line in info_lines:
            info_col.label(text=line)

# 注册属性
def register_properties():
    bpy.types.Scene.gradient_axis = bpy.props.EnumProperty(
        name="轴向",
        description="选择渐变方向的世界坐标轴",
        items=[
            ('X', "X轴", "沿X轴方向渐变（左黑右白）"),
            ('Y', "Y轴", "沿Y轴方向渐变（前黑后白）"),
            ('Z', "Z轴", "沿Z轴方向渐变（下黑上白）"),
        ],
        default='Z',
        update=update_gradient_preview
    )
    bpy.types.Scene.gradient_invert = bpy.props.BoolProperty(
        name="反转渐变",
        description="反转当前轴向的黑白渐变方向",
        default=False,
        update=update_gradient_preview
    )
    bpy.types.Scene.gradient_black_position = bpy.props.FloatProperty(
        name="黑场位置",
        description="颜色渐变中黑色端的位置",
        default=0.0,
        min=0.0,
        max=1.0,
        soft_min=0.0,
        soft_max=1.0,
        step=1,
        precision=3
    )
    bpy.types.Scene.gradient_white_position = bpy.props.FloatProperty(
        name="白场位置",
        description="颜色渐变中白色端的位置",
        default=1.0,
        min=0.0,
        max=1.0,
        soft_min=0.0,
        soft_max=1.0,
        step=1,
        precision=3
    )
    bpy.types.Scene.gradient_black_color = bpy.props.FloatVectorProperty(
        name="黑场颜色",
        description="颜色渐变的低值端颜色",
        subtype='COLOR',
        default=(0.0, 0.0, 0.0),
        min=0.0,
        max=1.0
    )
    bpy.types.Scene.gradient_white_color = bpy.props.FloatVectorProperty(
        name="白场颜色",
        description="颜色渐变的高值端颜色",
        subtype='COLOR',
        default=(1.0, 1.0, 1.0),
        min=0.0,
        max=1.0
    )
    bpy.types.Scene.gradient_resolution_x = bpy.props.IntProperty(
        name="宽度",
        description="导出图像的宽度（像素）",
        default=512,
        min=64,
        max=16384,
        step=512
    )
    bpy.types.Scene.gradient_resolution_y = bpy.props.IntProperty(
        name="高度",
        description="导出图像的高度（像素）",
        default=512,
        min=64,
        max=16384,
        step=512
    )
    bpy.types.Scene.gradient_color_depth = bpy.props.EnumProperty(
        name="色彩深度",
        description="图像色彩深度（更高的深度意味着更平滑的渐变）",
        items=[
            ('8', "8位 (256级)", "标准PNG，文件较小"),
            ('16', "16位 (65536级)", "更高精度，文件较大"),
        ],
        default='8'
    )
    bpy.types.Scene.gradient_sample_count = bpy.props.IntProperty(
        name="采样数",
        description="烘焙采样数（越高越精确，但耗时更长）",
        default=16,
        min=16,
        max=4096,
        step=16
    )
    bpy.types.Scene.gradient_use_float = bpy.props.BoolProperty(
        name="使用浮点缓冲",
        description="使用16位浮点缓冲区存储图像（提高渐变平滑度）",
        default=True
    )
    bpy.types.Scene.gradient_use_aa = bpy.props.BoolProperty(
        name="抗锯齿",
        description="启用烘焙抗锯齿（使边缘更平滑）",
        default=True
    )
    bpy.types.Scene.gradient_export_name = bpy.props.StringProperty(
        name="文件名",
        description="导出的文件名（不包含扩展名，留空则使用默认命名：模型名_轴向渐变遮罩）",
        default=""
    )
    bpy.types.Scene.gradient_export_path = bpy.props.StringProperty(
        name="保存位置",
        description="遮罩图像的保存目录（留空则保存在当前Blender文件所在目录）",
        subtype='DIR_PATH',
        default=""
    )

def unregister_properties():
    del bpy.types.Scene.gradient_axis
    del bpy.types.Scene.gradient_invert
    del bpy.types.Scene.gradient_black_position
    del bpy.types.Scene.gradient_white_position
    del bpy.types.Scene.gradient_black_color
    del bpy.types.Scene.gradient_white_color
    del bpy.types.Scene.gradient_resolution_x
    del bpy.types.Scene.gradient_resolution_y
    del bpy.types.Scene.gradient_color_depth
    del bpy.types.Scene.gradient_sample_count
    del bpy.types.Scene.gradient_use_float
    del bpy.types.Scene.gradient_use_aa
    del bpy.types.Scene.gradient_export_name
    del bpy.types.Scene.gradient_export_path

# 注册和注销
classes = [OBJECT_OT_PreviewGradientMask, OBJECT_OT_ExportGradientMask, VIEW3D_PT_GradientMaskPanel]

def register():
    register_translations()
    for cls in classes:
        bpy.utils.register_class(cls)
    register_properties()
    print(_("轴向渐变遮罩工具插件已加载 (AGMT)"))

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    unregister_properties()
    print(_("轴向渐变遮罩工具插件已卸载 (AGMT)"))
    unregister_translations()

if __name__ == "__main__":
    register()
