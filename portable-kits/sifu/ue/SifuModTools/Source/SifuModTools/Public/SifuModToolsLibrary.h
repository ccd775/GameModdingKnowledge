#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "SifuModToolsLibrary.generated.h"

class USkeletalMesh;
class UPhysicsAsset;
class UAnimBlueprint;

UCLASS()
class USifuModToolsLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()
public:
	/**
	 * Creates an NvCloth clothing asset from a mesh section and binds it to that section.
	 * Per-vertex max distance = VertexColor.R / 255 * MaxDistance (cm); R == 0 pins the vertex to the skinned pose.
	 * If AnimDrive > 0, VertexColor.G / 255 is written as the AnimDriveMultiplier mask.
	 * ConfigJson is applied onto the UClothConfigNv object (property names as in ClothConfigNv.h).
	 * Returns a short report, or a string starting with "ERROR".
	 */
	UFUNCTION(BlueprintCallable, Category = "SifuModTools")
	static FString CreateClothFromSection(USkeletalMesh* Mesh, int32 LodIndex, int32 SectionIndex, const FString& Name,
		UPhysicsAsset* CollisionAsset, float MaxDistance, bool bAnimDrive, const FString& ConfigJson);

	/**
	 * Proxy workflow: builds the clothing asset from the (low-res) section whose material slot is ProxySlot, removes that
	 * section from the mesh, and binds the asset to the render section whose slot is RenderSlot (mesh-to-mesh skinning).
	 * Masks come from the proxy vertex colors exactly like CreateClothFromSection. BackstopScale > 0 adds backstops
	 * (NvCloth separation spheres along the proxy normals): distance = G * BackstopScale, radius = B * BackstopScale (cm).
	 */
	UFUNCTION(BlueprintCallable, Category = "SifuModTools")
	static FString CreateClothProxy(USkeletalMesh* Mesh, const FString& ProxySlot, const FString& RenderSlot, const FString& Name,
		UPhysicsAsset* CollisionAsset, float MaxDistance, bool bAnimDrive, const FString& ConfigJson, float BackstopScale = 0.f);

	/** Removes all clothing assets from the mesh (unbinding their sections). */
	UFUNCTION(BlueprintCallable, Category = "SifuModTools")
	static int32 RemoveAllClothing(USkeletalMesh* Mesh);

	/**
	 * Fills a physics asset with simple shapes. Json: {"bodies":[{"bone":"thigh_l","type":"capsule|sphere|box",
	 * "center":[x,y,z],"rotation":[pitch,yaw,roll],"radius":r,"length":l,"extent":[x,y,z],"kinematic":true}],
	 * "constraints":true}. Coordinates are in the bone's local space (cm). Existing bodies are removed.
	 */
	UFUNCTION(BlueprintCallable, Category = "SifuModTools")
	static FString BuildPhysicsAsset(UPhysicsAsset* PhysicsAsset, USkeletalMesh* Mesh, const FString& Json);

	/** Creates (or loads) a PhysicsAsset at PackagePath/Name with the given preview mesh. */
	UFUNCTION(BlueprintCallable, Category = "SifuModTools")
	static UPhysicsAsset* CreatePhysicsAsset(const FString& PackagePath, const FString& Name, USkeletalMesh* PreviewMesh);

	/**
	 * Rebuilds the AnimGraph of a (post-process) anim blueprint as InputPose -> LocalToComponent -> RigidBody ->
	 * ComponentToLocal -> Output, applies RigidBodyJson onto the FAnimNode_RigidBody and compiles the blueprint.
	 */
	UFUNCTION(BlueprintCallable, Category = "SifuModTools")
	static FString SetupRigidBodyPostProcess(UAnimBlueprint* AnimBP, const FString& RigidBodyJson);

	/** JSON dump of the mesh reference skeleton (local transforms) for verification. */
	UFUNCTION(BlueprintCallable, Category = "SifuModTools")
	static FString DumpRefSkeleton(USkeletalMesh* Mesh);

	/** JSON summary of LOD0 sections (material index, verts, tris, clothing guid). */
	UFUNCTION(BlueprintCallable, Category = "SifuModTools")
	static FString DumpSections(USkeletalMesh* Mesh);

	/** Sets the post-process anim blueprint class on the mesh. */
	UFUNCTION(BlueprintCallable, Category = "SifuModTools")
	static void SetPostProcessAnimBlueprint(USkeletalMesh* Mesh, UClass* AnimClass);
};
