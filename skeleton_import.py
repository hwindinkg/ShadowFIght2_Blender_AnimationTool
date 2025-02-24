import bpy
import xml.etree.ElementTree as ET
import mathutils
import math

def create_capsule_from_points(name, pointA, pointB, radius):
    A = mathutils.Vector(pointA)
    B = mathutils.Vector(pointB)
    direction = B - A
    length = direction.length
    if length == 0:
        length = 0.001
    D = direction.normalized()
    
    cyl_depth = max(length - 2 * radius, 0.001)
    mid = (A + B) / 2.0
    rotation = direction.to_track_quat('Z', 'Y').to_euler()
    
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius,
        depth=cyl_depth,
        location=mid,
        rotation=rotation
    )
    cylinder = bpy.context.active_object
    cylinder.name = name + "_cyl"
    
    top_center = B - D * radius
    bottom_center = A + D * radius
    
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius,
        location=top_center,
        segments=32,
        ring_count=16
    )
    top_sphere = bpy.context.active_object
    top_sphere.name = name + "_top"
    
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius,
        location=bottom_center,
        segments=32,
        ring_count=16
    )
    bottom_sphere = bpy.context.active_object
    bottom_sphere.name = name + "_bottom"
    
    top_sphere.select_set(True)
    bottom_sphere.select_set(True)
    cylinder.select_set(True)
    bpy.context.view_layer.objects.active = cylinder
    bpy.ops.object.join()
    
    return cylinder

def import_capsules_from_skeleton(xml_text, scale_factor=0.1, radius_scale=0.1):
    tree = ET.ElementTree(ET.fromstring(xml_text))
    root = tree.getroot()
    
    nodes = {}
    nodes_elem = root.find("Nodes")
    if nodes_elem is None:
        print("В файле нет раздела Nodes.")
        return
    
    for elem in nodes_elem:
        if elem.get("Type") == "Node" or elem.tag.startswith("N"):
            try:
                x = float(elem.get("X", "0")) * scale_factor
                y = float(elem.get("Y", "0")) * scale_factor
                z = float(elem.get("Z", "0")) * scale_factor
                nodes[elem.tag] = (x, y, z)
            except Exception as e:
                print("Ошибка разбора узла", elem.tag, ":", e)
    
    cap_coll = bpy.data.collections.new("Character_Capsules_From_Skeleton")
    bpy.context.scene.collection.children.link(cap_coll)
    
    edges_elem = root.find("Edges")
    if edges_elem is None:
        print("В файле нет раздела Edges.")
        return
    
    capsule_count = 0
    for edge in edges_elem:
        if "Weapon" in edge.tag or edge.get("Type") != "Edge":
            continue
        
        end1 = edge.get("End1")
        end2 = edge.get("End2")
        if not end1 or not end2:
            continue
        if end1 not in nodes or end2 not in nodes:
            print("Не найдены узлы для ребра", edge.tag, ":", end1, end2)
            continue
        
        try:
            rad = float(edge.get("Radius", "1")) * radius_scale
        except:
            rad = 0.1
        
        capsule_obj = create_capsule_from_points(edge.tag, nodes[end1], nodes[end2], rad)
        capsule_count += 1
        
        if capsule_obj.name in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.unlink(capsule_obj)
        cap_coll.objects.link(capsule_obj)
    
    print(f"Создано {capsule_count} капсульных сегментов по данным skeleton.xml.")

filepath = "D:/sf/models/skeleton.xml"
with open(filepath, "r", encoding="windows-1251") as f:
    skeleton_xml = f.read()

import_capsules_from_skeleton(skeleton_xml, scale_factor=0.1, radius_scale=0.1)

